#!/bin/bash

# 정적 파일 동기화 스크립트
echo "🔄 정적 파일 동기화 시작..."

# rsync로 정적 파일만 동기화
rsync -avz --progress \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  static/ root@server24-5:/root/wndud/infotherapy/static/

echo "✅ 정적 파일 동기화 완료!"

# 서버에서 서비스 재시작
echo "🔄 서버 재시작 중..."
ssh root@server24-5 "cd /root/wndud/infotherapy && ./restart_server_quick.sh"

echo "🎉 동기화 및 재시작 완료!"
