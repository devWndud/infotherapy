#!/bin/bash

# Infotherapy 웹 서버 재시작 스크립트
echo "=== Infotherapy 서버 재시작 시작 ==="

# 1. 기존 프로세스 종료
echo "1. 기존 프로세스 종료 중..."
pkill -f gunicorn
pkill -f python
sleep 2

# 2. 프로젝트 디렉토리로 이동
echo "2. 프로젝트 디렉토리로 이동..."
cd /root/wndud/infotherapy

# 3. 가상환경 활성화
echo "3. 가상환경 활성화..."
source myenv/bin/activate

# 4. Git 최신 코드 가져오기
echo "4. Git 최신 코드 가져오기..."
git pull

# 5. 정적 파일 복사 (Nginx용)
echo "5. 정적 파일 복사..."
sudo cp -r /root/wndud/infotherapy/static/* /var/www/html/infotherapy/static/
sudo chown -R www-data:www-data /var/www/html/infotherapy/static/
sudo chmod -R 755 /var/www/html/infotherapy/static/

# 6. Gunicorn 서버 시작
echo "6. Gunicorn 서버 시작..."
nohup gunicorn --config gunicorn.conf.py application:application > app.log 2>&1 &

# 7. 서버 상태 확인
echo "7. 서버 상태 확인..."
sleep 3
echo "=== Gunicorn 프로세스 ==="
ps aux | grep gunicorn | grep -v grep

echo "=== 포트 8000 확인 ==="
netstat -tlnp | grep :8000

echo "=== 포트 5000 확인 ==="
netstat -tlnp | grep :5000

# 8. Nginx 재시작
echo "8. Nginx 재시작..."
sudo systemctl restart nginx

echo "=== 서버 재시작 완료 ==="
echo "로그 확인: tail -f /root/wndud/infotherapy/app.log"
