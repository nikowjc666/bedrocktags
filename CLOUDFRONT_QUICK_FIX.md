# CloudFront 超时问题 - 快速修复步骤

## 问题
查询配额过多时出现 CloudFront 错误 (504/503)，导致配额数据缺失。

## 快速修复（3 个步骤）

### 步骤 1: 更新 EC2 代码和配置
```bash
ssh -i "你的key.pem" ec2-user@你的EC2IP

cd ~/app
git pull origin main
sudo systemctl restart nginx
sudo systemctl restart bedrock-app

# 验证
sudo systemctl status bedrock-app
sudo journalctl -u bedrock-app -n 10
```

### 步骤 2: 更新 CloudFront Origin 超时（关键！）

**在 AWS Console 操作：**

1. 打开 CloudFront
2. 点击你的 Distribution ID
3. 左侧菜单 → **Origins** 
4. 点击编辑对应的 origin（通常是 EC2 IP）
5. 找到 **Origin Read Timeout** 字段
6. 改为 **300** （单位：秒）
7. 点击 **Save**

![配置位置参考]
```
Origins
├── Origin Domain Name: 16.192.29.171 (你的 EC2 IP)
├── Origin Read Timeout: 30 ← 改成 300
└── Origin Keep-alive Timeout: 5
```

8. 等待 CloudFront 状态变为 **Deployed**（通常 1-2 分钟）

### 步骤 3: 测试修复

**Web UI 测试：**
1. 访问 https://你的cloudfront域名/quotas
2. 选择 4-5 个区域 + 2-3 个模型
3. 点击查询
4. 应该在 10 秒内完成，无错误

**命令行测试：**
```bash
curl -X POST https://你的cloudfront域名/api/query_quotas \
  -H "Content-Type: application/json" \
  -H "X-CloudFront-Header: 你的密钥" \
  -d '{
    "access_key": "YOUR_AK",
    "secret_key": "YOUR_SK",
    "regions": ["us-east-1", "eu-west-1", "ap-southeast-1"],
    "quota_types": ["tpm", "tpd"],
    "models": ["Claude Sonnet 5"]
  }' --max-time 30
```

**预期结果：**
```json
{
  "ok": true,
  "total": 60,          // 应该有完整的配额
  "quotas": [...],
  "errors": []          // 无错误
}
```

## 验证指标

### CloudFront Dashboard
- **Error Rate**: 应该 <1%（改进前 5-15%）
- **Requests**: 正常流量
- **Data Transfer**: 完整

### 日志检查
```bash
sudo journalctl -u bedrock-app | grep "Found.*quotas"
# 输出示例：
# [Quota Query Debug] Found 60 quotas from code_map with 120 entries
```

## 修改了什么

1. **app.py** - 降低并发度，添加批处理
   - 每区域：40 → 10 并发
   - 区域间：10 → 5 并发
   - 批处理：每 10 个配额为一批，延迟 0.5s

2. **nginx.conf** - 增加超时配置
   - 读取超时：300s
   - 发送超时：300s
   - 连接超时：10s

3. **CloudFront** - 需要手动修改
   - Origin Read Timeout: 30s → 300s

## 如果还是有问题

### 问题 1: 仍然 504 超时
```bash
# 检查 nginx 是否重启了
sudo systemctl restart nginx
sudo systemctl status nginx

# 检查 Flask 应用
sudo systemctl status bedrock-app
sudo journalctl -u bedrock-app -n 50 | tail -20

# 清除 CloudFront 缓存
# AWS Console → CloudFront → Invalidations → Create Invalidation
# Paths: /api/query_quotas (或 /*)
```

### 问题 2: CloudFront 还是 Deploying
- 等待 5-10 分钟，不要急
- 可以继续用直接 EC2 IP 测试

### 问题 3: 配额仍然缺失
```bash
# 强制刷新配额缓存
curl -X POST https://你的cloudfront域名/api/query_quotas \
  -H "Content-Type: application/json" \
  -d '{
    ...your request...,
    "force_refresh": true
  }'
```

## 完整清单

- [ ] `git pull origin main` 更新代码
- [ ] `sudo systemctl restart nginx` 重启 nginx
- [ ] `sudo systemctl restart bedrock-app` 重启应用
- [ ] CloudFront Origin Read Timeout 改为 300
- [ ] CloudFront 状态变为 Deployed
- [ ] 多配额查询测试通过
- [ ] 错误率降至 <1%

## 时间预计

- 代码部署：3 分钟
- CloudFront 配置：1 分钟
- CloudFront 生效：2-5 分钟
- **总计：6-9 分钟**

## 相关文档

- 详细指南：`CLOUDFRONT_TIMEOUT_FIX.md`
- 快速总结：`QUICK_FIX_SUMMARY.md`
- 部署指南：`DEPLOYMENT_GUIDE.md`

---

**关键点：** 一定要更新 CloudFront Origin Read Timeout 为 300！
这是最重要的一步，只在 AWS Console 中操作。
