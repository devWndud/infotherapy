#!/bin/bash

# Nginx 설정 파일 수정 스크립트 (서버에서 실행)
NGINX_CONFIG="/etc/nginx/sites-enabled/infotherapy"

echo "🔧 Nginx 설정 파일 수정 중..."

# 백업 생성
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# 1. 포트 8000을 5000으로 변경
sudo sed -i 's/127\.0\.0\.1:8000/127.0.0.1:5000/g' "$NGINX_CONFIG"
sudo sed -i 's/server web:8000/server 127.0.0.1:5000/g' "$NGINX_CONFIG"

# 2. location /static 블록 찾아서 제거 (간단한 방법: 해당 라인들을 주석 처리)
# location /static 블록의 시작 라인 번호 찾기
START_LINE=$(sudo grep -n "location /static" "$NGINX_CONFIG" | head -1 | cut -d: -f1)

if [ ! -z "$START_LINE" ]; then
    echo "⚠️  location /static 블록을 찾았습니다. 주석 처리합니다 (라인 $START_LINE)"
    
    # Python을 사용하여 더 정확하게 처리
    sudo python3 << 'EOF'
import re
import sys

config_file = "/etc/nginx/sites-enabled/infotherapy"

with open(config_file, 'r') as f:
    lines = f.readlines()

result = []
in_static_block = False
brace_count = 0

for line in lines:
    # location /static 블록 시작
    if re.search(r'location\s+/static', line) and not line.strip().startswith('#'):
        in_static_block = True
        brace_count = line.count('{') - line.count('}')
        result.append('#' + line)
    elif in_static_block:
        brace_count += line.count('{') - line.count('}')
        result.append('#' + line)
        if brace_count == 0:
            in_static_block = False
    else:
        result.append(line)

with open(config_file, 'w') as f:
    f.writelines(result)

print("✅ location /static 블록을 주석 처리했습니다.")
EOF
fi

# 3. nginx 설정 테스트 및 재시작
echo "🧪 Nginx 설정 테스트..."
if sudo nginx -t; then
    echo "✅ Nginx 설정 파일이 유효합니다."
    sudo systemctl restart nginx
    echo "✅ Nginx 재시작 완료"
else
    echo "❌ Nginx 설정 오류! 백업에서 복원하세요."
    exit 1
fi

echo "✅ 완료!"

