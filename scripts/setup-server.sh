#!/bin/bash

# AWS 서버 초기 설정 스크립트
# Ubuntu 20.04+ 에서 실행

set -e

echo "🛠️  AWS 서버 초기 설정을 시작합니다..."

# 시스템 업데이트
echo "📦 시스템 패키지를 업데이트합니다..."
sudo apt update && sudo apt upgrade -y

# 필요한 패키지 설치
echo "🔧 필요한 패키지를 설치합니다..."
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx ufw curl

# 방화벽 설정
echo "🔥 방화벽을 설정합니다..."
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# 현재 사용자 홈 디렉토리 확인
USER_HOME=$(eval echo ~$USER)
echo "🏠 사용자 홈 디렉토리: $USER_HOME"

# 프로젝트 디렉토리로 이동
cd $USER_HOME

# Git 저장소 클론 (이미 있다면 스킵)
if [ ! -d "infotherapy" ]; then
    echo "📥 Git 저장소를 클론합니다..."
    git clone https://github.com/YOUR_USERNAME/infotherapy.git
fi

cd infotherapy

# 가상환경 생성 및 활성화
echo "🐍 Python 가상환경을 생성합니다..."
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
echo "📦 Python 의존성을 설치합니다..."
pip install -r requirements.txt

# 환경 변수 설정
echo "⚙️  환경 변수를 설정합니다..."
if [ ! -f ".env" ]; then
    cp env.example .env
    echo "🔧 .env 파일을 편집하여 실제 값으로 설정하세요!"
fi

# 데이터베이스 초기화
echo "🗄️  데이터베이스를 초기화합니다..."
python -c "from app import create_app; create_app()"

# 업로드 디렉토리 생성
echo "📁 업로드 디렉토리를 생성합니다..."
mkdir -p uploads

# SSL 인증서 설정
echo "🔒 SSL 인증서를 설정합니다..."
chmod +x scripts/setup-ssl.sh
./scripts/setup-ssl.sh $(curl -s http://169.254.169.254/latest/meta-data/public-hostname)

# Nginx 설정
echo "🌐 Nginx를 설정합니다..."
sudo cp nginx.conf /etc/nginx/sites-available/infotherapy
sudo ln -sf /etc/nginx/sites-available/infotherapy /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트 및 재시작
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# Systemd 서비스 설정
echo "🔧 Systemd 서비스를 설정합니다..."
# 서비스 파일에서 사용자 경로를 현재 사용자로 수정
sed "s|/home/ubuntu|$USER_HOME|g" systemd/infotherapy.service > /tmp/infotherapy.service
sudo cp /tmp/infotherapy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable infotherapy
sudo systemctl start infotherapy

# 배포 스크립트 실행 권한 부여
chmod +x deploy.sh

echo "✅ 서버 설정이 완료되었습니다!"
echo ""
echo "📋 다음 단계:"
echo "1. .env 파일을 편집하여 실제 값으로 설정"
echo "2. sudo systemctl status infotherapy 로 서비스 상태 확인"
echo "3. sudo journalctl -u infotherapy -f 로 로그 확인"
echo "4. https://$(curl -s http://169.254.169.254/latest/meta-data/public-hostname) 으로 접속 테스트"
echo ""
echo "🔄 이후 배포는 다음 명령어로:"
echo "   cd $USER_HOME/infotherapy"
echo "   ./deploy.sh"
