# Claude Haiku 5.5 更新说明

## 更新日期
2026-10-09

## 更新内容

已成功将 **Claude Haiku 5.5** 添加到 Bedrock Inference Profiles 管理系统中。

### 模型信息
- **模型 ID**: `anthropic.claude-haiku-5-5`
- **显示名称**: Claude Haiku 5.5
- **支持区域**:
  - US (美国): `us.anthropic.claude-haiku-5-5`
  - EU (欧洲): `eu.anthropic.claude-haiku-5-5`
  - Global (全球): `global.anthropic.claude-haiku-5-5`

### 模型特点
根据 Anthropic 官方发布（2026年10月7日）：
- 1M token 上下文窗口
- 最大输出 128K tokens
- 比 Haiku 4.5 便宜约 75%
- 最快、最高效的小型模型
- 适用场景：
  - 摘要生成
  - 数据压缩
  - 分类任务
  - 子代理（Subagent）
  - 实时客户支持
  - 浏览器自动化

### AWS Service Quota
根据 AWS Bedrock，Haiku 5.5 的默认配额为：
- **TPM (Tokens Per Minute)**: 10,000,000 (10M)
- 配额名称: `Global cross-region model inference tokens per minute for Anthropic Claude Haiku 5.5`

### 修改的文件

#### 1. app.py
**新增模型配置：**
在 `CLAUDE_VERSIONS` 列表中添加了 Haiku 5.5 配置：
```python
{
    "id": "anthropic.claude-haiku-5-5",
    "label": "Claude Haiku 5.5",
    "sources": {
        "us": "us.anthropic.claude-haiku-5-5",
        "eu": "eu.anthropic.claude-haiku-5-5",
        "global": "global.anthropic.claude-haiku-5-5",
    },
}
```

**改进配额查询逻辑：**
增强了 label 变体生成，支持更多命名格式（如 `haiku 5.5`, `haiku 5-5`, `haiku55` 等），提高新模型配额的匹配成功率。

**新增诊断端点：**
添加了 `/api/_diag/search_quota` 端点，用于搜索和调试配额映射。

#### 2. auto_provision.py
- 在 `MODEL_ALIAS` 字典中添加了 3 个别名：
  - `"haiku 5.5"`
  - `"haiku5.5"`
  - `"claude haiku 5.5"`
  
- 在 `CLAUDE_VERSIONS` 列表中添加了相同的模型配置
- 更新了帮助文本，添加了 "haiku 5.5" 示例

### 使用方法

#### 创建 Inference Profile
用户现在可以通过以下方式选择 Haiku 5.5：
1. 在模型下拉列表中选择 "Claude Haiku 5.5"
2. 在自动配置中使用别名: `haiku 5.5`, `haiku5.5`, 或 `claude haiku 5.5`

#### API 调用
- 通过 `/api/claude_versions` 获取所有模型（包含 Haiku 5.5）
- 通过 `/api/claude_45_versions` 获取 4.5+ 模型（包含 Haiku 5.5）
- 批量创建时可选择 Haiku 5.5

#### 查询配额
首次查询 Haiku 5.5 配额时，请勾选"强制刷新配额代码"以从 AWS 重新拉取最新的 Service Quotas。

### 配额查询问题及解决方案

#### 问题
Haiku 5.5 是新发布的模型（2026-10-07），旧的配额缓存中不包含其配额信息。

#### 解决方案
1. **Web 界面**：在配额查询页面勾选"强制刷新配额代码"
2. **API**：在请求中设置 `"force_refresh": true`
3. **手动清理**：删除 `outputs/quota_codes.json` 文件后重新查询

刷新后系统会自动从 AWS 拉取最新的配额映射，包括 Haiku 5.5 的 10M TPM 配额。

### 诊断工具

新增了诊断端点用于排查配额问题：

```bash
POST /api/_diag/search_quota
{
  "access_key": "YOUR_AK",
  "secret_key": "YOUR_SK",
  "keyword": "haiku",
  "force_refresh": true
}
```

这将返回所有包含 "haiku" 关键词的配额及其代码和值。

### 验证结果
✓ 已通过 Python 语法检查  
✓ Haiku 5.5 已添加到 CLAUDE_BY_ID  
✓ Haiku 5.5 已添加到 CLAUDE_45_BY_ID  
✓ 3 个别名正常工作  
✓ 模型总数从 15 增加到 16  
✓ 配额查询逻辑已优化以支持新模型  
✓ AWS 已发布 Haiku 5.5 配额（10M TPM）  

### 向后兼容性
- 此更新完全向后兼容
- 不影响现有的 Haiku 4.5 及其他模型
- 现有的 Inference Profiles 不受影响
- 配额缓存会在下次查询时自动更新

## 参考资料
- [Anthropic 官方公告](https://www.anthropic.com/claude-haiku-5-5)
- [AWS Bedrock Haiku 5.5 介绍](https://aws.amazon.com/blogs/machine-learning/introducing-claude-haiku-5-5-on-aws/)
- AWS Bedrock Service Quotas 已包含 Haiku 5.5 配额
