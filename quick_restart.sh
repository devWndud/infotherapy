#!/bin/bash

# 빠른 서버 재시작 스크립트 (502 에러용)
echo "=== 빠른 서버 재시작 ==="

# 1. 프로세스 정리
rm -f /tmp/gunicorn.pid
pkill -9 -f gunicorn
pkill -9 -f python

# 2. 서버 시작
cd /root/wndud/infotherapy
source myenv/bin/activate
nohup gunicorn --bind 127.0.0.1:5000 application:application > app.log 2>&1 &

# 3. Nginx 재시작
sudo systemctl restart nginx

# 4. 상태 확인
sleep 2
ps aux | grep gunicorn | grep -v grep
netstat -tlnp | grep :5000

echo "=== 재시작 완료 ==="
