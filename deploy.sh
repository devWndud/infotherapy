#!/bin/bash

# Git 배포 스크립트
# AWS 서버에서 실행: ./deploy.sh

set -e

echo "🚀 Infotherapy 배포를 시작합니다..."

# 최신 코드 가져오기
echo "📥 Git에서 최신 코드를 가져옵니다..."
git pull origin main

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "🐍 가상환경을 활성화합니다..."
    source venv/bin/activate
fi

# 의존성 설치
echo "📦 Python 의존성을 설치합니다..."
pip install -r requirements.txt

# 환경 변수 설정 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다. env.example을 복사합니다..."
    cp env.example .env
    echo "🔧 .env 파일을 편집하여 실제 값으로 설정하세요!"
fi

# 자산 버전 갱신 (정적 캐시 무효화)
export ASSET_VERSION=$(date +%Y%m%d%H%M%S)

# 데이터베이스 초기화
echo "🗄️  데이터베이스를 초기화합니다..."
python -c "from app import create_app; create_app()"

# SSL 인증서 확인
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    echo "🔒 SSL 인증서가 없습니다. 설정 스크립트를 실행합니다..."
    chmod +x scripts/setup-ssl.sh
    ./scripts/setup-ssl.sh $(hostname)
fi

# 업로드 디렉토리 생성
echo "📁 업로드 디렉토리를 생성합니다..."
mkdir -p uploads

# 권한 설정
echo "🔐 파일 권한을 설정합니다..."
chmod 755 uploads
chmod 644 infotherapy.db 2>/dev/null || true

# Gunicorn 프로세스 확인 및 재시작
echo "🔄 Gunicorn 프로세스를 재시작합니다..."
if pgrep -f gunicorn > /dev/null; then
    echo "기존 Gunicorn 프로세스를 종료합니다..."
    pkill -f gunicorn
    sleep 2
fi

# Gunicorn 시작
echo "🚀 Gunicorn을 시작합니다..."
nohup env ASSET_VERSION=$ASSET_VERSION gunicorn --config gunicorn.conf.py application:application > gunicorn.log 2>&1 &

# 정적 파일 동기화 (Nginx가 /var/www/html/infotherapy/static 제공 시)
WEB_STATIC_DIR=/var/www/html/infotherapy/static
if [ -d "static" ]; then
    echo "🧩 정적 파일을 Nginx 웹 루트로 동기화합니다..."
    sudo mkdir -p "$WEB_STATIC_DIR"
    sudo rsync -a --delete static/ "$WEB_STATIC_DIR"/
    # 권한 정리 (www-data 사용자 기준)
    if id www-data >/dev/null 2>&1; then
        sudo chown -R www-data:www-data "$WEB_STATIC_DIR"
        sudo find "$WEB_STATIC_DIR" -type d -exec chmod 755 {} \;
        sudo find "$WEB_STATIC_DIR" -type f -exec chmod 644 {} \;
    fi
fi

# Nginx 설정 확인 및 재시작
if command -v nginx &> /dev/null; then
    echo "🌐 Nginx 설정을 확인합니다..."
    sudo nginx -t
    if [ $? -eq 0 ]; then
        echo "Nginx를 재시작합니다..."
        sudo systemctl restart nginx
    else
        echo "⚠️  Nginx 설정에 오류가 있습니다. 수동으로 확인하세요."
    fi
fi

# 헬스 체크
echo "🏥 애플리케이션 상태를 확인합니다..."
sleep 5
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ 배포가 성공적으로 완료되었습니다!"
    echo "🌐 애플리케이션 URL: https://$(hostname)"
else
    echo "❌ 배포 중 오류가 발생했습니다. 로그를 확인하세요:"
    echo "   tail -f gunicorn.log"
fi

echo "📋 유용한 명령어:"
echo "   로그 확인: tail -f gunicorn.log"
echo "   프로세스 확인: ps aux | grep gunicorn"
echo "   서비스 상태: sudo systemctl status nginx"
