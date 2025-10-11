
from flask import Flask, request, jsonify, send_from_directory, url_for
import yt_dlp
import os
import re
import json
import subprocess
import tempfile
from alternative_downloader import get_video_info_alternative, extract_video_id

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YDL_OPTS = {
    "quiet": True,
    "skip_download": True,
    "nocheckcertificate": True,
    "geo_bypass": True,
    "extract_flat": False,
    "forcejson": True,
    "noplaylist": True,
    "source_address": "0.0.0.0",
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    },
    "format": "bestaudio/best",
    "extractor_retries": 5,
    "fragment_retries": 5,
    "retries": 5,
    "sleep_interval": 2,
    "max_sleep_interval": 10,
    "sleep_interval_subtitles": 1,
    "sleep_interval_requests": 1,
    "sleep_interval_subtitles": 1,
    "sleep_interval_requests": 1,
    "extractor_args": {
        "youtube": {
            "player_client": ["android_music", "android_creator", "android", "web"],
            "player_skip": ["webpage"],
            "innertube_host": "music.youtube.com",
            "innertube_key": "AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30",
        }
    },
}

@app.post("/extract")
def extract():
    data = request.get_json(force=True)
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "missing url"}), 400

    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            # If playlist mixed in, pick the first entry
            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            title = info.get("title") or "Unknown"
            author = info.get("uploader") or info.get("channel") or "Unknown"
            duration = info.get("duration")  # seconds
            thumbnail = info.get("thumbnail")

            # Find direct audio URL from formats
            audio_url = None
            ext = None
            formats = info.get("formats") or []
            # Prefer m4a/mp4 first
            preferred = []
            fallback = []
            for f in formats:
                # Only audio
                if f.get("vcodec") in (None, "none"):
                    (preferred if (f.get("ext") in ("m4a", "mp4")) else fallback).append(f)
            selected = None
            if preferred:
                selected = max(preferred, key=lambda x: x.get("abr") or 0)
            elif fallback:
                selected = max(fallback, key=lambda x: x.get("abr") or 0)

            if selected:
                audio_url = selected.get("url")
                ext = selected.get("ext")

            return jsonify({
                "audio_url": audio_url,
                "title": title,
                "author": author,
                "thumbnail_url": thumbnail,
                "ext": ext,
                "duration": duration
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _sanitize(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip()[:120]


@app.post("/download")
def download():
    data = request.get_json(force=True)
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "missing url"}), 400

    # 간단한 설정으로 변경 (test_simple.py와 동일)
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title).80s-%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }

    try:
        # 먼저 yt-dlp로 시도
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            title = info.get("title") or "Unknown"
            author = info.get("uploader") or info.get("channel") or "Unknown"
            duration = info.get("duration")
            thumbnail = info.get("thumbnail")
            ext = info.get("ext")

            # Resolve output filename
            base = f"{_sanitize(title)}-{info.get('id')}"
            filename = None
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(base) and f.endswith(f".{ext}"):
                    filename = f
                    break
            if not filename:
                # Fallback: scan by id
                vid = info.get("id")
                for f in os.listdir(DOWNLOAD_DIR):
                    if f.endswith(f".{ext}") and (vid in f):
                        filename = f
                        break
            if not filename:
                return jsonify({"error": "file not found after download"}), 500

            # Build public URL
            base_url = request.host_url.rstrip('/')
            file_url = f"{base_url}/files/{filename}"

            return jsonify({
                "file_url": file_url,
                "title": title,
                "author": author,
                "thumbnail_url": thumbnail,
                "ext": ext,
                "duration": duration,
            }), 200
    except Exception as e:
        print(f"yt-dlp 실패, 대체 방법 시도: {e}")
        
        # 대체 방법: 비디오 ID 추출 후 정보만 가져오기
        try:
            video_id = extract_video_id(url)
            if not video_id:
                return jsonify({"error": "비디오 ID를 추출할 수 없습니다"}), 400
            
            # 대체 방법으로 비디오 정보 가져오기
            alt_info = get_video_info_alternative(video_id)
            if not alt_info['success']:
                return jsonify({"error": "비디오 정보를 가져올 수 없습니다"}), 500
            
            # 임시 파일 생성 (실제 다운로드는 불가능하지만 정보는 제공)
            return jsonify({
                "error": "다운로드 실패 - yt-dlp가 YouTube 차단으로 인해 작동하지 않습니다",
                "title": alt_info['title'],
                "author": alt_info['author'],
                "thumbnail_url": alt_info['thumbnail'],
                "video_id": video_id,
                "suggestion": "다른 서버나 VPN을 사용해보세요"
            }), 503
            
        except Exception as alt_e:
            return jsonify({"error": f"모든 방법 실패: {str(alt_e)}"}), 500


@app.get('/files/<path:filename>')
def files(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=False)


@app.post('/delete')
def delete_file():
    data = request.get_json(force=True)
    file_url = data.get('file_url')
    filename = data.get('filename')
    target = None

    try:
        if filename:
            target = os.path.join(DOWNLOAD_DIR, os.path.basename(filename))
        elif file_url:
            # Extract filename part if it matches our /files route
            # e.g., http://host/files/<filename>
            marker = '/files/'
            if marker in file_url:
                candidate = file_url.split(marker, 1)[1]
                target = os.path.join(DOWNLOAD_DIR, os.path.basename(candidate))

        if not target:
            return jsonify({'error': 'missing filename or file_url'}), 400

        # Ensure path is inside DOWNLOAD_DIR
        target = os.path.abspath(target)
        if not target.startswith(os.path.abspath(DOWNLOAD_DIR)):
            return jsonify({'error': 'invalid path'}), 400

        if os.path.exists(target):
            os.remove(target)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.get('/version')
def get_version():
    """Check app version and return update info if needed"""
    try:
        # Read version info from version.json
        version_file = os.path.join(BASE_DIR, 'version.json')
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                version_info = json.load(f)
        else:
            # Default version info
            version_info = {
                "latest_version": "1.0.0",
                "min_version": "1.0.0",
                "update_available": False,
                "force_update": False,
                "download_url": "",
                "release_notes": "Initial release"
            }
        
        # Get client version from query param
        client_version = request.args.get('version', '1.0.0')
        
        # Simple version comparison (assumes semantic versioning)
        def version_tuple(v):
            return tuple(map(int, v.split('.')))
        
        latest_version = version_info.get('latest_version', '1.0.0')
        min_version = version_info.get('min_version', '1.0.0')
        
        client_tuple = version_tuple(client_version)
        latest_tuple = version_tuple(latest_version)
        min_tuple = version_tuple(min_version)
        
        # Check if update is needed
        needs_update = client_tuple < latest_tuple
        force_update = client_tuple < min_tuple
        
        response = {
            "current_version": client_version,
            "latest_version": latest_version,
            "min_version": min_version,
            "update_available": needs_update,
            "force_update": force_update,
            "download_url": version_info.get('download_url', ''),
            "release_notes": version_info.get('release_notes', ''),
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # pip install flask yt-dlp
    # python server.py
    app.run(host="0.0.0.0", port=8080)
    