#!/bin/bash

# 현재 디렉토리에서 빠른 설정 스크립트
# 이미 프로젝트 디렉토리에 있다고 가정

set -e

echo "🚀 Infotherapy 빠른 설정을 시작합니다..."

# 현재 디렉토리 확인
CURRENT_DIR=$(pwd)
echo "📁 현재 디렉토리: $CURRENT_DIR"

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
mkdir -p ssl
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    # 자체 서명 인증서 생성
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/key.pem \
        -out ssl/cert.pem \
        -subj "/C=KR/ST=Seoul/L=Seoul/O=Infotherapy/CN=localhost"
    echo "✅ 자체 서명 SSL 인증서가 생성되었습니다."
fi

# Gunicorn으로 직접 실행
echo "🚀 Gunicorn을 시작합니다..."
echo "📋 다음 명령어로 애플리케이션을 실행하세요:"
echo "   source venv/bin/activate"
echo "   gunicorn --config gunicorn.conf.py application:application"
echo ""
echo "🌐 애플리케이션 URL: http://localhost:8000"
echo "🔒 HTTPS URL: https://localhost:8000 (자체 서명 인증서)"

# 배포 스크립트 실행 권한 부여
chmod +x deploy.sh

echo "✅ 설정이 완료되었습니다!"
