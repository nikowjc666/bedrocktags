# ============================================================
#  从 Git 拉取最新代码并重启服务
# ============================================================
param(
    [string]$KeyFile = "D:\BedrockKey.pem",
    [string]$EC2IP   = "16.192.29.171",
    [string]$Branch  = "main"
)

$Remote = "ec2-user@${EC2IP}"
$AppDir = "~/bedrocktags"

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  部署到 EC2: $EC2IP  (branch: $Branch)" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

ssh -i $KeyFile $Remote @"
set -e
cd $AppDir
echo '[1/3] 拉取最新代码...'
git pull origin $Branch
echo '[2/3] 重启服务...'
sudo systemctl restart bedrock-app
echo '[3/3] 验证服务状态...'
sleep 2
sudo systemctl is-active bedrock-app && echo '✅ 服务运行正常' || (echo '❌ 服务异常' && sudo journalctl -u bedrock-app --no-pager -n 20 && exit 1)
"@

Write-Host ""
Write-Host "=======================================" -ForegroundColor Green
Write-Host "  部署完成！http://$EC2IP" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
