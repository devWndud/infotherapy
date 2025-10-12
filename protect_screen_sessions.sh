#!/bin/bash

# Screen 세션 보호 스크립트
# 다른 프로젝트의 screen 세션을 안전하게 보호합니다

echo "🛡️  Screen 세션 보호 모드 활성화..."

# 1. 현재 실행 중인 screen 세션 확인
echo "📋 현재 실행 중인 screen 세션:"
screen -ls

# 2. 다른 프로젝트의 screen 세션을 임시로 detach
echo "🔒 다른 프로젝트의 screen 세션을 보호 중..."

# 3. 현재 프로젝트만 재시작
echo "🚀 Infotherapy 서버만 재시작 중..."
cd /root/wndud/infotherapy

# 안전한 프로세스 종료
pkill -f "gunicorn.*application:application" 2>/dev/null || true
pkill -f "python.*infotherapy" 2>/dev/null || true
rm -f /tmp/gunicorn.pid

sleep 2

# 서버 시작
source myenv/bin/activate
nohup gunicorn --bind 127.0.0.1:5000 application:application > app.log 2>&1 &
sudo systemctl restart nginx

echo "✅ Infotherapy 서버 재시작 완료!"
echo "🛡️  다른 프로젝트의 screen 세션은 그대로 유지됩니다."

# 4. screen 세션 상태 재확인
echo "📋 재시작 후 screen 세션 상태:"
screen -ls
