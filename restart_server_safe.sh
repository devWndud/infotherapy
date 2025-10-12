#!/bin/bash

# 안전한 서버 재부팅 스크립트
# 다른 프로젝트의 screen 세션과 프로세스를 보호합니다

echo "🚀 Infotherapy 서버 재시작 중..."

# 현재 프로젝트 디렉토리로 이동
cd /root/wndud/infotherapy

# 1. 현재 프로젝트의 gunicorn 프로세스만 종료 (PID 파일 기반)
if [ -f "/tmp/gunicorn.pid" ]; then
    echo "📋 기존 Gunicorn PID 파일 발견, 안전하게 종료 중..."
    PID=$(cat /tmp/gunicorn.pid)
    if kill -0 $PID 2>/dev/null; then
        kill -TERM $PID
        sleep 3
        if kill -0 $PID 2>/dev/null; then
            echo "⚠️  강제 종료 중..."
            kill -KILL $PID
        fi
    fi
    rm -f /tmp/gunicorn.pid
else
    echo "🔍 PID 파일이 없습니다. 프로세스 이름으로 검색 중..."
    # 현재 디렉토리의 gunicorn 프로세스만 찾아서 종료
    PIDS=$(pgrep -f "gunicorn.*application:application")
    if [ ! -z "$PIDS" ]; then
        echo "📋 Gunicorn 프로세스 발견: $PIDS"
        kill -TERM $PIDS
        sleep 3
        # 여전히 실행 중이면 강제 종료
        for pid in $PIDS; do
            if kill -0 $pid 2>/dev/null; then
                echo "⚠️  강제 종료: $pid"
                kill -KILL $pid
            fi
        done
    fi
fi

# 2. 현재 디렉토리의 Python 프로세스만 종료 (더 안전한 방법)
echo "🐍 현재 프로젝트의 Python 프로세스 정리 중..."
# 현재 디렉토리에서 실행된 Python 프로세스만 찾기
PIDS=$(ps aux | grep -E "python.*infotherapy" | grep -v grep | awk '{print $2}')
if [ ! -z "$PIDS" ]; then
    echo "📋 Python 프로세스 발견: $PIDS"
    kill -TERM $PIDS
    sleep 2
fi

# 3. 잠시 대기
echo "⏳ 프로세스 정리 완료, 잠시 대기 중..."
sleep 2

# 4. 가상환경 활성화 및 서버 시작
echo "🔧 가상환경 활성화 중..."
source myenv/bin/activate

# 5. Gunicorn 서버 시작 (PID 파일과 함께)
echo "🚀 Gunicorn 서버 시작 중..."
nohup gunicorn --bind 127.0.0.1:5000 --pid /tmp/gunicorn.pid application:application > app.log 2>&1 &

# 6. 서버 시작 확인
sleep 3
if [ -f "/tmp/gunicorn.pid" ]; then
    PID=$(cat /tmp/gunicorn.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "✅ 서버가 성공적으로 시작되었습니다! (PID: $PID)"
    else
        echo "❌ 서버 시작에 실패했습니다."
        exit 1
    fi
else
    echo "❌ PID 파일이 생성되지 않았습니다."
    exit 1
fi

# 7. Nginx 재시작
echo "🌐 Nginx 재시작 중..."
sudo systemctl restart nginx

# 8. 최종 상태 확인
echo "📊 최종 상태 확인 중..."
echo "🔍 Gunicorn 프로세스:"
ps aux | grep gunicorn | grep -v grep
echo "🔍 포트 5000 상태:"
netstat -tlnp | grep :5000
echo "🔍 Nginx 상태:"
sudo systemctl status nginx --no-pager -l

echo "🎉 서버 재시작이 완료되었습니다!"
echo "📝 로그 확인: tail -f app.log"
