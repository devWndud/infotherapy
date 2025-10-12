#!/bin/bash

# 개선된 서버 재부팅 스크립트
# 기존 명령어를 개선하여 다른 프로젝트 보호

echo "🚀 Infotherapy 서버 재시작 중..."

# 현재 프로젝트 디렉토리로 이동
cd /root/wndud/infotherapy

# 1. 현재 프로젝트의 gunicorn만 종료 (더 구체적인 패턴)
echo "🛑 Gunicorn 프로세스 종료 중..."
pkill -f "gunicorn.*application:application" 2>/dev/null || true

# 2. 현재 프로젝트의 Python 프로세스만 종료 (더 안전)
echo "🐍 Python 프로세스 정리 중..."
pkill -f "python.*infotherapy" 2>/dev/null || true

# 3. PID 파일 정리
rm -f /tmp/gunicorn.pid

# 4. 잠시 대기
sleep 2

# 5. 서버 시작
echo "🚀 새 서버 시작 중..."
source myenv/bin/activate
nohup gunicorn --bind 127.0.0.1:5000 application:application > app.log 2>&1 &

# 6. Nginx 재시작
echo "🌐 Nginx 재시작 중..."
sudo systemctl restart nginx

# 7. 상태 확인
echo "📊 상태 확인 중..."
ps aux | grep gunicorn | grep -v grep
netstat -tlnp | grep :5000

echo "✅ 서버 재시작 완료!"
echo "📝 로그: tail -f app.log"
