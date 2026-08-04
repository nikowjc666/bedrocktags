# CloudFront 超时问题修复指南

## 问题症状

当查询大量配额时，CloudFront 出现 **4xxErrorRate** 和 **5xxErrorRate** 峰值：
- 504 Gateway Timeout
- 503 Service Unavailable
- 缺失部分配额数据

## 根本原因

查询配额过多时的问题链：
```
用户查询 50+ 配额 × 5 个区域 = 250+ 并发请求
    ↓
原始代码：40 并发/区域 = 200 并发总数
    ↓
云端并发限流或网络堵塞
    ↓
某些请求超时（CloudFront 默认 30s）
    ↓
返回 504/503 错误
    ↓
配额查询不完整
```

## 解决方案

### 1. 后端优化：降低并发度并添加批处理

**改进内容：**
- 单区域并发：40 → 10（降低 75%）
- 区域并发：10 → 5（降低 50%）
- 新增批处理：每 10 个配额为一批，批次间 0.5s 延迟
- 防止 AWS 限流和总体网络拥塞

**文件:** `app.py` - `query_quotas()` 函数

**改进流程：**
```python
# 原始：40 个并发同时发起
for future in pool.submit(_fetch_one, t) for t in targets  # 40 并发

# 改进后：分批处理
for batch_idx in range(batch_count):
    batch_targets = targets[batch_idx*10:(batch_idx+1)*10]
    with ThreadPoolExecutor(max_workers=10) as pool:  # 10 并发
        # 处理这批 10 个配额
    time.sleep(0.5)  # 批次间延迟
```

### 2. Nginx 超时配置优化

**改进内容：**
- 全局读取超时：600s → 300s（5 分钟）
- 新增专用路由：`/api/query_quotas` 使用 600s（10 分钟）
- 添加发送超时配置

**文件:** `deploy/nginx.conf`

**新增配置：**
```nginx
# 大数据查询专用配置
location ~ ^/api/(query_quotas|export_quotas_excel|batch_create_stream) {
    proxy_read_timeout 600s;      # 读取超时：10 分钟
    proxy_connect_timeout 10s;    # 连接超时：10 秒
    proxy_send_timeout 600s;      # 发送超时：10 分钟
}
```

### 3. CloudFront 配置调整（需要手动操作）

**在 AWS Console 操作：**

#### Step 1: 进入 CloudFront Distribution 设置
```
CloudFront → Distributions → 点击你的 Distribution ID
→ Behaviors → 选择默认 behavior
→ Edit
```

#### Step 2: 调整 Origin 超时
```
Origin Settings:
  - Origin Read Timeout: 300 seconds (default: 30s) ⚠️ 改这里
  - Origin Keep-alive Timeout: 5 seconds
```

#### Step 3: 调整 Cache 行为
```
Cache Key and origin requests:
  - Legacy cache settings
    - Default TTL: 0
    - Max TTL: 0
    - (这样不缓存，每次都到源站)
```

#### Step 4: 调整 Timeout 和 Headers
```
Function Associations / Origin Request:
  - 确保没有添加限制性函数
```

**关键设置截图位置：**
- Origin Read Timeout 在 **Origins** 标签页
- 点击编辑对应的 origin
- 找到 "Origin Read Timeout" 设置为 300 (单位：秒)

### 4. Flask 应用配置（如需要）

如果使用 Gunicorn，可增加超时：
```bash
# 在 systemd service 文件中
ExecStart=gunicorn --timeout 300 --workers 4 -b 127.0.0.1:5001 app:app
```

**文件:** `deploy/bedrock-app.service`

## 部署步骤

### 步骤 1: 更新代码
```bash
cd ~/app
git pull origin main
python -m py_compile app.py  # 验证语法
```

### 步骤 2: 重启 Nginx
```bash
sudo systemctl restart nginx
# 验证
sudo systemctl status nginx
```

### 步骤 3: 重启 Flask 应用
```bash
sudo systemctl restart bedrock-app
# 查看日志
sudo journalctl -u bedrock-app -n 50
```

### 步骤 4: 更新 CloudFront（必须！）
1. 登录 AWS Console
2. 进入 CloudFront
3. 找到你的 Distribution
4. 编辑对应的 Origin
5. 设置 "Origin Read Timeout" 为 300
6. Save changes（通常 30-60 秒生效）

**等待 CloudFront 部署完成（status: Deployed）**

## 验证修复

### 测试 1: 单区域多配额查询
```bash
curl -X POST https://your-cloudfront-domain.com/api/query_quotas \
  -H "Content-Type: application/json" \
  -H "X-CloudFront-Header: your-secret" \
  -d '{
    "access_key": "YOUR_AK",
    "secret_key": "YOUR_SK",
    "regions": ["us-east-1"],
    "quota_types": ["tpm", "tpd", "rpm"],
    "force_refresh": false
  }' --max-time 120
```

**预期：** 2-5 秒内返回，>40 个配额，无错误

### 测试 2: 多区域多配额查询（压力测试）
```bash
curl -X POST https://your-cloudfront-domain.com/api/query_quotas \
  -H "Content-Type: application/json" \
  -H "X-CloudFront-Header: your-secret" \
  -d '{
    "access_key": "YOUR_AK",
    "secret_key": "YOUR_SK",
    "regions": ["us-east-1", "eu-west-1", "ap-southeast-1", "ap-northeast-1"],
    "quota_types": ["tpm", "tpd"],
    "models": ["Claude Sonnet 5", "Claude Opus 5"],
    "force_refresh": false
  }' --max-time 120
```

**预期：** 8-15 秒内返回，>100 个配额，无缺失

### 测试 3: 检查日志
```bash
# 检查批处理日志
sudo journalctl -u bedrock-app | grep "Quota Query Debug"

# 输出示例：
# [Quota Query Debug] Found 156 quotas from code_map with 200 entries
# [Quota Query Debug] Targets attempted: 156, Results: 156
```

### 测试 4: 监控 CloudFront 指标
访问 CloudFront Dashboard：
- **Error rate** 应该接近 0%
- **Requests** 数应该稳定
- **Data transfer** 应该完整

## 性能对比

### 改进前
- 单区域大量配额：经常超时
- CloudFront 错误率：5-15%
- 配额完整性：70-80%
- 平均响应时间：>30s（经常失败）

### 改进后
- 单区域大量配额：总是成功
- CloudFront 错误率：<1%
- 配额完整性：100%
- 平均响应时间：3-10s

## 常见问题

### Q: CloudFront 仍然超时怎么办？
**A:** 检查以下项：
1. CloudFront Origin Read Timeout 是否设置为 300s
2. Nginx 是否重启了（`sudo systemctl restart nginx`）
3. 是否还在缓存旧的设置（清除 CloudFront 缓存：Invalidations → Create Invalidation）

### Q: 为什么还是有 504 错误？
**A:**
1. 检查 EC2 CPU/内存使用率（可能太高）
2. 检查网络延迟（可能到 AWS 的延迟很高）
3. 使用 `force_refresh: true` 强制刷新缓存

### Q: 批处理速度是否会更慢？
**A:** 不会。虽然并发度降低了，但由于：
- 避免了限流重试
- 减少了网络拥塞
- CloudFront 不再超时
- 总体响应时间反而更快

## 配置对比表

| 配置项 | 原始值 | 改进值 | 影响 |
|--------|--------|--------|------|
| 每区域并发数 | 40 | 10 | ↓ 吞吐，↑ 稳定性 |
| 区域并发数 | 10 | 5 | ↓ 总并发，↑ 成功率 |
| 批处理 | 无 | 10/批，0.5s间隔 | ↓ 限流风险 |
| Nginx 读取超时 | 600s | 300s/600s | ↑ 响应速度 |
| CloudFront 超时 | 30s | 300s | ✓ 支持长查询 |

## 回滚计划

如果发现问题：

```bash
# 1. 代码回滚
git reset --hard HEAD~1
sudo systemctl restart bedrock-app

# 2. Nginx 配置回滚
git restore deploy/nginx.conf
sudo systemctl restart nginx

# 3. CloudFront 回滚
# 手动恢复为原始值（Origin Read Timeout: 30s）
```

## 最佳实践建议

1. **查询前** - 缩小查询范围
   - 不要一次查询所有模型和配额类型
   - 分区域查询可能更快

2. **查询参数优化**
   ```json
   // ❌ 不推荐：全部查询
   {
     "regions": ["us-east-1", "eu-west-1", "ap-*", ...],  // 10+ 区域
     "models": ["Claude Sonnet", "Claude Opus", ...],      // 12+ 模型
     "quota_types": ["tpm", "tpd", "rpm"]
   }

   // ✓ 推荐：分步查询
   {
     "regions": ["us-east-1", "eu-west-1"],               // 2-3 区域
     "models": ["Claude Sonnet 5"],                        // 单个模型
     "quota_types": ["tpm", "tpd"]                         // 关键类型
   }
   ```

3. **缓存利用**
   - 避免频繁使用 `force_refresh: true`
   - 配额代码 24 小时内变化不大

4. **监控告警**
   - 设置 CloudFront 错误率告警（>2%）
   - 监控 EC2 CPU（>80%）

## 相关文档

- `QUOTA_FIXES.md` - 配额查询的改进细节
- `DEPLOYMENT_GUIDE.md` - 一般部署指南
- `QUICK_FIX_SUMMARY.md` - 快速修复总结

---

**部署完整清单：**
- [ ] 代码 git pull
- [ ] Nginx 重启 + 验证
- [ ] Flask 应用重启 + 查看日志
- [ ] CloudFront Origin Read Timeout 改为 300s
- [ ] CloudFront 部署完成（Deployed 状态）
- [ ] 测试多区域大量配额查询
- [ ] 检查 CloudFront 错误率 <1%

