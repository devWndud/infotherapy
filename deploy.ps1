# Git 배포 스크립트 (Windows PowerShell)
# AWS 서버에서 실행: .\deploy.ps1

Write-Host "🚀 Infotherapy 배포를 시작합니다..." -ForegroundColor Green

try {
    # 최신 코드 가져오기
    Write-Host "📥 Git에서 최신 코드를 가져옵니다..." -ForegroundColor Yellow
    git pull origin main

    # 가상환경 활성화 (있는 경우)
    if (Test-Path "venv") {
        Write-Host "🐍 가상환경을 활성화합니다..." -ForegroundColor Yellow
        & "venv\Scripts\Activate.ps1"
    }

    # 의존성 설치
    Write-Host "📦 Python 의존성을 설치합니다..." -ForegroundColor Yellow
    pip install -r requirements.txt

    # 환경 변수 설정 확인
    if (!(Test-Path ".env")) {
        Write-Host "⚠️  .env 파일이 없습니다. env.example을 복사합니다..." -ForegroundColor Yellow
        Copy-Item "env.example" ".env"
        Write-Host "🔧 .env 파일을 편집하여 실제 값으로 설정하세요!" -ForegroundColor Red
    }

    # 데이터베이스 초기화
    Write-Host "🗄️  데이터베이스를 초기화합니다..." -ForegroundColor Yellow
    python -c "from app import create_app; create_app()"

    # SSL 인증서 확인
    if (!(Test-Path "ssl\cert.pem") -or !(Test-Path "ssl\key.pem")) {
        Write-Host "🔒 SSL 인증서가 없습니다. 설정 스크립트를 실행합니다..." -ForegroundColor Yellow
        & ".\scripts\setup-ssl.ps1" -Domain $env:COMPUTERNAME
    }

    # 업로드 디렉토리 생성
    Write-Host "📁 업로드 디렉토리를 생성합니다..." -ForegroundColor Yellow
    if (!(Test-Path "uploads")) {
        New-Item -ItemType Directory -Path "uploads"
    }

    # Gunicorn 프로세스 확인 및 재시작
    Write-Host "🔄 Gunicorn 프로세스를 재시작합니다..." -ForegroundColor Yellow
    $gunicornProcess = Get-Process -Name "gunicorn" -ErrorAction SilentlyContinue
    if ($gunicornProcess) {
        Write-Host "기존 Gunicorn 프로세스를 종료합니다..." -ForegroundColor Yellow
        Stop-Process -Name "gunicorn" -Force
        Start-Sleep -Seconds 2
    }

    # Gunicorn 시작
    Write-Host "🚀 Gunicorn을 시작합니다..." -ForegroundColor Yellow
    Start-Process -FilePath "gunicorn" -ArgumentList "--config", "gunicorn.conf.py", "application:application" -WindowStyle Hidden

    # 헬스 체크
    Write-Host "🏥 애플리케이션 상태를 확인합니다..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ 배포가 성공적으로 완료되었습니다!" -ForegroundColor Green
            Write-Host "🌐 애플리케이션 URL: https://$($env:COMPUTERNAME)" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ 배포 중 오류가 발생했습니다. 로그를 확인하세요." -ForegroundColor Red
    }

    Write-Host "📋 유용한 명령어:" -ForegroundColor Cyan
    Write-Host "   프로세스 확인: Get-Process gunicorn" -ForegroundColor White
    Write-Host "   서비스 중지: Stop-Process -Name gunicorn" -ForegroundColor White

} catch {
    Write-Host "❌ 배포 중 오류가 발생했습니다: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
