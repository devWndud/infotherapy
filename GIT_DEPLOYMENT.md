# Git 배포 가이드

이 가이드는 Git을 사용하여 AWS 서버에 Infotherapy 애플리케이션을 배포하는 방법을 설명합니다.

## 🚀 빠른 시작

### 1. GitHub 저장소 준비

```bash
# 로컬에서 Git 저장소 초기화
git init
git add .
git commit -m "Initial commit"

# GitHub에 저장소 생성 후 연결
git remote add origin https://github.com/YOUR_USERNAME/infotherapy.git
git branch -M main
git push -u origin main
```

### 2. AWS 서버 초기 설정

```bash
# AWS EC2 인스턴스에 접속
ssh -i your-key.pem ubuntu@your-server-ip

# 서버 초기 설정 스크립트 실행
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/infotherapy/main/scripts/setup-server.sh | bash
```

### 3. 환경 변수 설정

```bash
# .env 파일 편집
nano .env

# 다음 값들을 실제 값으로 변경:
FLASK_SECRET=your-super-secret-key-here
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
ADMIN_EMAILS=admin@yourdomain.com
```

### 4. 서비스 시작

```bash
# 서비스 상태 확인
sudo systemctl status infotherapy

# 서비스 시작 (자동으로 시작됨)
sudo systemctl start infotherapy

# 로그 확인
sudo journalctl -u infotherapy -f
```

## 🔄 배포 프로세스

### 자동 배포 (권장)

```bash
# AWS 서버에서 실행
cd /home/ubuntu/infotherapy
./deploy.sh
```

### 수동 배포

```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 의존성 업데이트
source venv/bin/activate
pip install -r requirements.txt

# 3. 서비스 재시작
sudo systemctl restart infotherapy

# 4. 상태 확인
sudo systemctl status infotherapy
```

## 📁 프로젝트 구조

```
infotherapy/
├── app.py                 # Flask 애플리케이션
├── application.py         # WSGI 진입점
├── requirements.txt       # Python 의존성
├── gunicorn.conf.py      # Gunicorn 설정
├── nginx.conf            # Nginx 설정
├── deploy.sh             # Linux 배포 스크립트
├── deploy.ps1            # Windows 배포 스크립트
├── .ebextensions/        # Elastic Beanstalk 설정
├── scripts/
│   ├── setup-server.sh   # 서버 초기 설정
│   ├── setup-ssl.sh      # SSL 인증서 설정
│   └── setup-ssl.ps1     # Windows SSL 설정
├── systemd/
│   └── infotherapy.service  # Systemd 서비스
├── ssl/                  # SSL 인증서 (자동 생성)
├── uploads/              # 업로드된 파일
└── templates/            # HTML 템플릿
```

## 🔧 서비스 관리

### Systemd 서비스 명령어

```bash
# 서비스 상태 확인
sudo systemctl status infotherapy

# 서비스 시작
sudo systemctl start infotherapy

# 서비스 중지
sudo systemctl stop infotherapy

# 서비스 재시작
sudo systemctl restart infotherapy

# 서비스 자동 시작 설정
sudo systemctl enable infotherapy

# 서비스 자동 시작 해제
sudo systemctl disable infotherapy
```

### 로그 확인

```bash
# 실시간 로그 확인
sudo journalctl -u infotherapy -f

# 최근 로그 확인
sudo journalctl -u infotherapy --lines=50

# 오류 로그만 확인
sudo journalctl -u infotherapy -p err
```

## 🌐 Nginx 관리

### Nginx 명령어

```bash
# Nginx 상태 확인
sudo systemctl status nginx

# Nginx 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx

# Nginx 로그 확인
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### SSL 인증서 갱신

```bash
# Let's Encrypt 인증서 갱신
sudo certbot renew

# 수동 갱신 테스트
sudo certbot renew --dry-run
```

## 🔒 보안 설정

### 방화벽 설정

```bash
# UFW 상태 확인
sudo ufw status

# SSH 포트만 열기 (기본)
sudo ufw allow ssh

# HTTP/HTTPS 포트 열기
sudo ufw allow 'Nginx Full'

# 방화벽 활성화
sudo ufw enable
```

### SSL 인증서 설정

```bash
# Let's Encrypt 인증서 발급
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 자체 서명 인증서 (테스트용)
./scripts/setup-ssl.sh yourdomain.com
```

## 🐛 문제 해결

### 일반적인 문제들

1. **서비스가 시작되지 않음**
   ```bash
   # 로그 확인
   sudo journalctl -u infotherapy -f
   
   # 포트 사용 확인
   sudo netstat -tlnp | grep :8000
   ```

2. **SSL 인증서 오류**
   ```bash
   # 인증서 파일 확인
   ls -la ssl/
   
   # Nginx 설정 테스트
   sudo nginx -t
   ```

3. **데이터베이스 오류**
   ```bash
   # 데이터베이스 파일 권한 확인
   ls -la infotherapy.db
   
   # 데이터베이스 재생성
   python -c "from app import create_app; create_app()"
   ```

4. **업로드 디렉토리 오류**
   ```bash
   # 업로드 디렉토리 권한 설정
   sudo chown -R ubuntu:ubuntu uploads/
   chmod 755 uploads/
   ```

### 로그 파일 위치

- **애플리케이션 로그**: `sudo journalctl -u infotherapy`
- **Nginx 액세스 로그**: `/var/log/nginx/access.log`
- **Nginx 오류 로그**: `/var/log/nginx/error.log`
- **시스템 로그**: `/var/log/syslog`

## 🔄 CI/CD 설정 (선택사항)

### GitHub Actions 워크플로우

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to AWS
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.KEY }}
        script: |
          cd /home/ubuntu/infotherapy
          git pull origin main
          ./deploy.sh
```

## 📊 모니터링

### 헬스 체크

```bash
# 애플리케이션 상태 확인
curl -f http://localhost:8000/

# HTTPS 상태 확인
curl -f https://yourdomain.com/
```

### 성능 모니터링

```bash
# CPU 사용률 확인
top -p $(pgrep gunicorn)

# 메모리 사용률 확인
ps aux | grep gunicorn

# 디스크 사용률 확인
df -h
```

## 🎯 최적화 팁

1. **Gunicorn 워커 수 조정**
   ```bash
   # CPU 코어 수에 맞게 조정
   # gunicorn.conf.py에서 workers = 2 * CPU_CORES + 1
   ```

2. **Nginx 캐싱 설정**
   ```nginx
   # nginx.conf에 추가
   location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

3. **데이터베이스 최적화**
   ```bash
   # SQLite 최적화
   sqlite3 infotherapy.db "PRAGMA journal_mode=WAL;"
   ```

이제 Git을 사용하여 쉽게 배포할 수 있습니다! 🚀
