#!/bin/bash

# 빠른 서버 재부팅 스크립트 (다른 프로젝트 보호)
echo "🚀 Infotherapy 서버 빠른 재시작..."

cd /root/wndud/infotherapy

# 1. 현재 프로젝트의 gunicorn만 종료
echo "🛑 기존 서버 종료 중..."
pkill -f "gunicorn.*application:application" 2>/dev/null || true
rm -f /tmp/gunicorn.pid

# 2. 잠시 대기
sleep 2

# 3. 서버 시작
echo "🚀 새 서버 시작 중..."
source myenv/bin/activate
nohup gunicorn --bind 127.0.0.1:5000 --pid /tmp/gunicorn.pid application:application > app.log 2>&1 &

# 4. Nginx 재시작
sudo systemctl restart nginx

echo "✅ 완료! 다른 프로젝트는 그대로 유지됩니다."
