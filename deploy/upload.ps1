# ============================================================
#  上传项目到 EC2
#  使用前修改下面 3 个变量
# ============================================================
param(
    [string]$KeyFile  = "C:\Users\你的用户名\Downloads\your-key.pem",
    [string]$EC2IP    = "1.2.3.4",
    [string]$CFSecret = "my-super-secret-2024"   # 自定义，和 CloudFront 里填的一致
)

$EC2User = "ec2-user"
$Remote  = "${EC2User}@${EC2IP}"

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  上传项目到 EC2: $EC2IP" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# 1. 在服务器创建目录结构
Write-Host "`n[1/3] 创建远程目录..." -ForegroundColor Yellow
ssh -i $KeyFile -o StrictHostKeyChecking=no $Remote "mkdir -p ~/app/deploy ~/app/templates ~/app/static"

# 2. 上传文件（只上传必要文件）
Write-Host "[2/3] 上传文件..." -ForegroundColor Yellow

$files = @(
    "app.py",
    "requirements.txt"
)
foreach ($f in $files) {
    scp -i $KeyFile "D:\bedrock-inference-profiles\$f" "${Remote}:~/app/$f"
    Write-Host "  ✓ $f"
}

# 上传目录
scp -i $KeyFile -r "D:\bedrock-inference-profiles\templates" "${Remote}:~/app/"
Write-Host "  ✓ templates/"

scp -i $KeyFile -r "D:\bedrock-inference-profiles\static" "${Remote}:~/app/"
Write-Host "  ✓ static/"

scp -i $KeyFile -r "D:\bedrock-inference-profiles\deploy" "${Remote}:~/app/"
Write-Host "  ✓ deploy/"

# 3. 执行安装脚本
Write-Host "[3/3] 执行安装脚本..." -ForegroundColor Yellow
ssh -i $KeyFile $Remote "chmod +x ~/app/deploy/setup_ec2.sh && bash ~/app/deploy/setup_ec2.sh '$CFSecret'"

Write-Host ""
Write-Host "=======================================" -ForegroundColor Green
Write-Host "  完成！EC2 地址: http://$EC2IP" -ForegroundColor Green
Write-Host "  下一步：去 AWS Console 配置 CloudFront" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
