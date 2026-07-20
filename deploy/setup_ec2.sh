#!/bin/bash
# 在 EC2 上执行：bash setup_ec2.sh
set -e

CF_SECRET="${1:-REPLACE_WITH_YOUR_SECRET}"   # 第一个参数传入自定义密钥
APP_DIR="/home/ec2-user/bedrocktags"

echo ""
echo "========================================="
echo "  Bedrock Manager — EC2 Setup Script"
echo "========================================="
echo ""

# ── 1. 系统更新 ───────────────────────────────────────────────
echo "[1/6] 更新系统..."
sudo dnf update -y -q
sudo dnf install -y python3 python3-pip nginx -q

# ── 2. 安装 Python 依赖 ───────────────────────────────────────
echo "[2/6] 安装 Python 依赖..."
cd "$APP_DIR"
pip3 install -q -r requirements.txt
pip3 install -q gunicorn

# ── 3. 创建日志目录 ───────────────────────────────────────────
echo "[3/6] 创建日志目录..."
sudo mkdir -p /var/log/bedrock-app
sudo chown ec2-user:ec2-user /var/log/bedrock-app

# ── 4. 配置 Nginx ─────────────────────────────────────────────
echo "[4/6] 配置 Nginx..."
# 替换 nginx 配置中的密钥
sed "s/REPLACE_WITH_YOUR_SECRET/${CF_SECRET}/g" "$APP_DIR/deploy/nginx.conf" \
    | sudo tee /etc/nginx/conf.d/bedrock.conf > /dev/null

# 删除默认配置
sudo rm -f /etc/nginx/conf.d/default.conf
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# ── 5. 配置 Flask App 服务 ────────────────────────────────────
echo "[5/6] 配置应用服务..."
sudo cp "$APP_DIR/deploy/bedrock-app.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bedrock-app
sudo systemctl restart bedrock-app

# ── 6. 验证 ──────────────────────────────────────────────────
echo "[6/6] 验证部署..."
sleep 3

if sudo systemctl is-active --quiet bedrock-app; then
    echo "  ✅ Flask 应用运行正常"
else
    echo "  ❌ Flask 应用启动失败，查看日志："
    sudo journalctl -u bedrock-app --no-pager -n 20
    exit 1
fi

if sudo systemctl is-active --quiet nginx; then
    echo "  ✅ Nginx 运行正常"
else
    echo "  ❌ Nginx 启动失败"
    exit 1
fi

PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "  EC2 公网 IP : $PUBLIC_IP"
echo "  本地测试    : curl -H 'x-cloudfront-secret: ${CF_SECRET}' http://$PUBLIC_IP/"
echo ""
echo "  下一步：在 CloudFront 配置 Origin = $PUBLIC_IP"
echo "========================================="
