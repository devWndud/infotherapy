# AWS HTTPS 배포 가이드

이 가이드는 Infotherapy Flask 애플리케이션을 AWS에서 HTTPS로 배포하는 방법을 설명합니다.

## 배포 옵션

### 1. AWS Elastic Beanstalk (권장)

#### 사전 준비
1. AWS CLI 설치 및 구성
2. EB CLI 설치: `pip install awsebcli`

#### 배포 단계

1. **EB 애플리케이션 초기화**
```bash
eb init infotherapy-app --platform python-3.11 --region ap-northeast-2
```

2. **환경 생성**
```bash
eb create production --instance-type t3.micro
```

3. **SSL 인증서 설정**
   - AWS Certificate Manager에서 SSL 인증서 요청
   - 도메인 검증 완료
   - `.ebextensions/04_https.config`에서 인증서 ARN 업데이트

4. **환경 변수 설정**
```bash
eb setenv FLASK_SECRET=your-secret-key
eb setenv SMTP_HOST=your-smtp-host
eb setenv SMTP_USER=your-smtp-user
eb setenv SMTP_PASS=your-smtp-password
eb setenv ADMIN_EMAILS=admin@example.com
```

5. **배포**
```bash
eb deploy
```

### 2. AWS EC2 + Docker

#### 사전 준비
1. EC2 인스턴스 생성 (Ubuntu 20.04+)
2. Docker 및 Docker Compose 설치

#### 배포 단계

1. **코드 업로드**
```bash
scp -r . ec2-user@your-ec2-ip:/home/ec2-user/infotherapy
```

2. **SSL 인증서 생성**
```bash
# Let's Encrypt 사용 (권장)
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com

# 또는 자체 서명 인증서 (테스트용)
mkdir ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=Infotherapy/CN=yourdomain.com"
```

3. **환경 변수 설정**
```bash
cp .env.example .env
# .env 파일 편집
```

4. **Docker Compose로 실행**
```bash
docker-compose up -d
```

### 3. AWS ECS (컨테이너 오케스트레이션)

#### 사전 준비
1. ECS 클러스터 생성
2. ECR 리포지토리 생성

#### 배포 단계

1. **Docker 이미지 빌드 및 푸시**
```bash
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com
docker build -t infotherapy .
docker tag infotherapy:latest YOUR_ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/infotherapy:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/infotherapy:latest
```

2. **ECS 태스크 정의 생성**
3. **ECS 서비스 생성**
4. **Application Load Balancer 설정**

## SSL 인증서 설정

### Let's Encrypt (무료, 권장)

1. **Certbot 설치**
```bash
sudo apt update
sudo apt install certbot
```

2. **인증서 발급**
```bash
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

3. **자동 갱신 설정**
```bash
sudo crontab -e
# 다음 라인 추가
0 12 * * * /usr/bin/certbot renew --quiet
```

### AWS Certificate Manager (ACM)

1. **AWS Console에서 인증서 요청**
2. **도메인 검증 완료**
3. **ALB/CloudFront에 인증서 연결**

## 보안 설정

### 1. 환경 변수 보안
- `.env` 파일을 `.gitignore`에 추가
- AWS Systems Manager Parameter Store 사용 권장

### 2. 데이터베이스 보안
- RDS 사용 권장 (SQLite 대신)
- 암호화 활성화
- VPC 내부 배치

### 3. 파일 업로드 보안
- 파일 타입 검증
- 파일 크기 제한
- 바이러스 스캔

## 모니터링 및 로깅

### 1. CloudWatch 로그
```python
import logging
import boto3

# CloudWatch 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### 2. 헬스 체크
```bash
# 헬스 체크 엔드포인트 추가
curl -f https://yourdomain.com/health || exit 1
```

## 성능 최적화

### 1. 정적 파일 CDN
- CloudFront 설정
- S3 버킷에 정적 파일 저장

### 2. 데이터베이스 최적화
- RDS 읽기 전용 복제본
- 연결 풀링

### 3. 캐싱
- Redis 캐시 추가
- 세션 저장소로 Redis 사용

## 백업 및 복구

### 1. 데이터베이스 백업
```bash
# SQLite 백업
cp infotherapy.db infotherapy_backup_$(date +%Y%m%d).db

# RDS 스냅샷 (RDS 사용 시)
aws rds create-db-snapshot --db-instance-identifier infotherapy-db --db-snapshot-identifier infotherapy-backup-$(date +%Y%m%d)
```

### 2. 파일 백업
```bash
# S3에 업로드된 파일 백업
aws s3 sync uploads/ s3://your-backup-bucket/uploads/
```

## 문제 해결

### 1. SSL 인증서 오류
- 인증서 경로 확인
- 권한 설정 확인
- 인증서 만료일 확인

### 2. 연결 오류
- 보안 그룹 설정 확인
- 포트 설정 확인
- 방화벽 설정 확인

### 3. 성능 문제
- 로그 확인
- 리소스 사용량 모니터링
- 데이터베이스 쿼리 최적화

## 비용 최적화

### 1. 인스턴스 크기 조정
- 사용량에 따라 인스턴스 크기 조정
- 스팟 인스턴스 사용 고려

### 2. 스토리지 최적화
- 불필요한 파일 정리
- S3 Intelligent Tiering 사용

### 3. 모니터링
- CloudWatch 비용 알림 설정
- 사용하지 않는 리소스 정리
