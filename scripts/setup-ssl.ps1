# SSL 인증서 설정 스크립트 (Windows PowerShell)
# 사용법: .\scripts\setup-ssl.ps1 yourdomain.com

param(
    [Parameter(Mandatory=$true)]
    [string]$Domain
)

Write-Host "SSL 인증서 설정을 시작합니다: $Domain"

# SSL 디렉토리 생성
if (!(Test-Path "ssl")) {
    New-Item -ItemType Directory -Path "ssl"
}

# 자체 서명 인증서 생성 (테스트용)
Write-Host "자체 서명 인증서를 생성합니다..."

# OpenSSL이 설치되어 있는지 확인
$opensslPath = Get-Command openssl -ErrorAction SilentlyContinue
if ($opensslPath) {
    Write-Host "OpenSSL을 사용하여 인증서를 생성합니다..."
    & openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout "ssl\key.pem" -out "ssl\cert.pem" -subj "/C=KR/ST=Seoul/L=Seoul/O=Infotherapy/CN=$Domain"
} else {
    Write-Host "OpenSSL이 설치되어 있지 않습니다. PowerShell로 자체 서명 인증서를 생성합니다..."
    
    # PowerShell로 자체 서명 인증서 생성
    $cert = New-SelfSignedCertificate -DnsName $Domain, "www.$Domain" -CertStoreLocation "Cert:\CurrentUser\My" -KeyLength 2048 -KeyAlgorithm RSA -HashAlgorithm SHA256
    
    # 인증서를 파일로 내보내기
    $certPath = "ssl\cert.pem"
    $keyPath = "ssl\key.pem"
    
    # PFX 파일로 내보내기
    $pfxPath = "ssl\temp.pfx"
    $password = ConvertTo-SecureString -String "temp123" -Force -AsPlainText
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $password
    
    # OpenSSL이 없으면 간단한 메시지 출력
    Write-Host "PowerShell로 생성된 인증서는 PFX 형식입니다."
    Write-Host "PEM 형식으로 변환하려면 OpenSSL을 설치하거나 온라인 도구를 사용하세요."
    Write-Host "임시로 PFX 파일이 생성되었습니다: $pfxPath"
}

Write-Host "SSL 설정이 완료되었습니다!"
Write-Host "Docker Compose를 실행하세요: docker-compose up -d"
