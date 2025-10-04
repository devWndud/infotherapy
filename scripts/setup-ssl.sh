#!/bin/bash

# SSL 인증서 설정 스크립트
# 사용법: ./scripts/setup-ssl.sh yourdomain.com

DOMAIN=$1

if [ -z "$DOMAIN" ]; then
    echo "사용법: $0 yourdomain.com"
    exit 1
fi

echo "SSL 인증서 설정을 시작합니다: $DOMAIN"

# Let's Encrypt 설치
if ! command -v certbot &> /dev/null; then
    echo "Certbot을 설치합니다..."
    sudo apt update
    sudo apt install -y certbot
fi

# SSL 디렉토리 생성
mkdir -p ssl

# Let's Encrypt 인증서 발급
echo "Let's Encrypt 인증서를 발급합니다..."
sudo certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

if [ $? -eq 0 ]; then
    echo "인증서 발급 성공!"
    
    # 인증서 파일을 프로젝트 디렉토리로 복사
    sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/cert.pem
    sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/key.pem
    
    # 권한 설정
    sudo chown $USER:$USER ssl/cert.pem ssl/key.pem
    chmod 644 ssl/cert.pem
    chmod 600 ssl/key.pem
    
    echo "인증서 파일이 ssl/ 디렉토리에 복사되었습니다."
    echo "자동 갱신을 설정합니다..."
    
    # 자동 갱신 설정
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/cert.pem && cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/key.pem") | crontab -
    
    echo "SSL 설정이 완료되었습니다!"
    echo "Docker Compose를 실행하세요: docker-compose up -d"
else
    echo "인증서 발급 실패. 자체 서명 인증서를 생성합니다..."
    
    # 자체 서명 인증서 생성 (테스트용)
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/key.pem \
        -out ssl/cert.pem \
        -subj "/C=KR/ST=Seoul/L=Seoul/O=Infotherapy/CN=$DOMAIN"
    
    chmod 644 ssl/cert.pem
    chmod 600 ssl/key.pem
    
    echo "자체 서명 인증서가 생성되었습니다. (테스트용)"
fi
