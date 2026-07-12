#!/bin/sh

# INFOTHERAPY .env 파일 생성 스크립트
# 사용법: bash setup-env.sh

cd "$(dirname "$0")" || exit 1

cat > .env << 'EOF'
# Flask Configuration
FLASK_SECRET=your-secret-key-change-me
FLASK_ENV=production

# Database Configuration
DATABASE_URL=sqlite:///infotherapy.db

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=devwndud@gmail.com
SMTP_PASS=cnltvkwhjhgcijfq
SMTP_FROM=devwndud@gmail.com
ADMIN_EMAILS=imnotwndud@gmail.com

# AWS Configuration (if using AWS services)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=ap-northeast-2

# SSL Configuration
SSL_CERT_PATH=/etc/ssl/certs/cert.pem
SSL_KEY_PATH=/etc/ssl/private/key.pem
EOF

echo "✓ .env 파일이 생성되었습니다."
echo ""
cat .env | grep SMTP