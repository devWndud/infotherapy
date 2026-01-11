#!/bin/bash

# Nginx 설정 파일 수정 스크립트
# Static 파일을 Flask로 프록시하도록 설정

echo "🔧 Nginx 설정 파일 수정 중..."

NGINX_CONFIG="/etc/nginx/sites-enabled/infotherapy"

if [ ! -f "$NGINX_CONFIG" ]; then
    echo "❌ Nginx 설정 파일을 찾을 수 없습니다: $NGINX_CONFIG"
    exit 1
fi

# 백업 생성
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ 백업 생성: ${NGINX_CONFIG}.backup.*"

# 포트 8000을 5000으로 변경 (upstream flask)
sudo sed -i 's/server 127\.0\.0\.1:8000;/server 127.0.0.1:5000;/g' "$NGINX_CONFIG"
sudo sed -i 's/server web:8000;/server 127.0.0.1:5000;/g' "$NGINX_CONFIG"
echo "✅ Upstream 포트를 5000으로 변경"

# location /static 블록이 있는지 확인하고 제거
if grep -q "location /static" "$NGINX_CONFIG"; then
    echo "⚠️  location /static 블록을 찾았습니다. 주석 처리합니다."
    
    # location /static 블록을 찾아서 주석 처리 (더 안전한 방법)
    # Python 스크립트를 사용하여 더 정확하게 처리
    sudo python3 << 'PYTHON_SCRIPT'
import re
import sys

config_file = "/etc/nginx/sites-enabled/infotherapy"

try:
    with open(config_file, 'r') as f:
        content = f.read()
    
    # location /static 블록을 주석 처리
    # 패턴: location /static 또는 location /static/ 시작부터 다음 location 또는 } 블록 끝까지
    pattern = r'(\s+)(location\s+/static[^{]*\{[^}]*\})'
    
    def comment_block(match):
        indent = match.group(1)
        block = match.group(2)
        # 각 줄을 주석 처리
        commented = '\n'.join(['#' + line if line.strip() else line for line in block.split('\n')])
        return indent + commented
    
    # 더 간단한 방법: location /static 라인부터 닫는 } 까지 찾기
    lines = content.split('\n')
    result_lines = []
    in_static_block = False
    brace_count = 0
    
    for line in lines:
        if re.search(r'location\s+/static', line) and not line.strip().startswith('#'):
            in_static_block = True
            brace_count = line.count('{') - line.count('}')
            result_lines.append('#' + line)
        elif in_static_block:
            brace_count += line.count('{') - line.count('}')
            result_lines.append('#' + line)
            if brace_count == 0:
                in_static_block = False
        else:
            result_lines.append(line)
    
    new_content = '\n'.join(result_lines)
    
    with open(config_file, 'w') as f:
        f.write(new_content)
    
    print("✅ location /static 블록을 주석 처리했습니다.")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    sys.exit(1)
PYTHON_SCRIPT
fi

# nginx 설정 테스트
echo "🧪 Nginx 설정 테스트..."
if sudo nginx -t; then
    echo "✅ Nginx 설정 파일이 유효합니다."
    echo "🔄 Nginx를 재시작합니다..."
    sudo systemctl restart nginx
    echo "✅ Nginx 재시작 완료"
else
    echo "❌ Nginx 설정 파일에 오류가 있습니다."
    echo "📋 백업 파일에서 복원하려면:"
    echo "   sudo cp ${NGINX_CONFIG}.backup.* $NGINX_CONFIG"
    exit 1
fi

echo ""
echo "✅ 설정 수정 완료!"
echo "📋 확인 사항:"
echo "   1. Gunicorn이 포트 5000에서 실행 중인지 확인: ps aux | grep gunicorn"
echo "   2. Nginx 상태 확인: sudo systemctl status nginx"
echo "   3. Static 파일 테스트: curl -I http://127.0.0.1:5000/static/js/main.js"

