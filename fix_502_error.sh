#!/bin/bash

# 502 에러 해결 및 서버 재시작 스크립트
echo "=== 502 에러 해결 및 서버 재시작 시작 ==="

# 1. PID 파일 삭제
echo "1. PID 파일 삭제..."
rm -f /tmp/gunicorn.pid

# 2. 모든 프로세스 강제 종료
echo "2. 기존 프로세스 강제 종료..."
pkill -9 -f gunicorn
pkill -9 -f python
sleep 2

# 3. 프로젝트 디렉토리로 이동
echo "3. 프로젝트 디렉토리로 이동..."
cd /root/wndud/infotherapy

# 4. 가상환경 활성화
echo "4. 가상환경 활성화..."
source myenv/bin/activate

# 5. Gunicorn 서버 시작 (5000번 포트)
echo "5. Gunicorn 서버 시작 (5000번 포트)..."
nohup gunicorn --bind 127.0.0.1:5000 application:application > app.log 2>&1 &

# 6. 서버 상태 확인
echo "6. 서버 상태 확인..."
sleep 3
echo "=== Gunicorn 프로세스 ==="
ps aux | grep gunicorn | grep -v grep

echo "=== 포트 5000 확인 ==="
netstat -tlnp | grep :5000

# 7. Nginx 재시작
echo "7. Nginx 재시작..."
sudo systemctl restart nginx

# 8. Nginx 상태 확인
echo "8. Nginx 상태 확인..."
sudo systemctl status nginx --no-pager

# 9. 로컬 테스트
echo "9. 로컬 테스트..."
curl -I http://localhost:5000 2>/dev/null | head -1

echo "=== 502 에러 해결 완료 ==="
echo "웹사이트 접속: https://infotherapy.kro.kr"
echo "로그 확인: tail -f /root/wndud/infotherapy/app.log"
