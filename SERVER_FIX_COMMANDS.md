# 서버에서 Nginx 설정 수정 명령어

서버에서 다음 명령어들을 순서대로 실행하세요:

## 방법 1: 한 줄씩 실행 (권장)

```bash
cd /root/wndud/infotherapy

# 1. 백업 생성
sudo cp /etc/nginx/sites-enabled/infotherapy /etc/nginx/sites-enabled/infotherapy.backup

# 2. 포트 8000을 5000으로 변경
sudo sed -i 's/127\.0\.0\.1:8000/127.0.0.1:5000/g' /etc/nginx/sites-enabled/infotherapy
sudo sed -i 's/server web:8000/server 127.0.0.1:5000/g' /etc/nginx/sites-enabled/infotherapy

# 3. location /static 블록 주석 처리 (Python 스크립트 사용)
sudo python3 << 'PYEOF'
import re

config_file = "/etc/nginx/sites-enabled/infotherapy"

with open(config_file, 'r') as f:
    lines = f.readlines()

result = []
in_static_block = False
brace_count = 0

for line in lines:
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
PYEOF

# 4. nginx 설정 테스트
sudo nginx -t

# 5. nginx 재시작
sudo systemctl restart nginx

# 6. 확인
curl -I http://127.0.0.1:5000/static/js/main.js
```

## 방법 2: 스크립트 파일 사용

```bash
cd /root/wndud/infotherapy

# 스크립트 파일 생성
cat > fix_nginx.sh << 'EOF'
#!/bin/bash
NGINX_CONFIG="/etc/nginx/sites-enabled/infotherapy"
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup"
sudo sed -i 's/127\.0\.0\.1:8000/127.0.0.1:5000/g' "$NGINX_CONFIG"
sudo sed -i 's/server web:8000/server 127.0.0.1:5000/g' "$NGINX_CONFIG"
sudo python3 << 'PYEOF'
import re
config_file = "/etc/nginx/sites-enabled/infotherapy"
with open(config_file, 'r') as f:
    lines = f.readlines()
result = []
in_static_block = False
brace_count = 0
for line in lines:
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
PYEOF
sudo nginx -t && sudo systemctl restart nginx
EOF

chmod +x fix_nginx.sh
sudo ./fix_nginx.sh
```

## 문제 발생 시 복원

```bash
sudo cp /etc/nginx/sites-enabled/infotherapy.backup /etc/nginx/sites-enabled/infotherapy
sudo nginx -t
sudo systemctl restart nginx
```

