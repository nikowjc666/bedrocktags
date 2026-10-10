# GPT 模型配置更新说明

## 更新日期
2026-10-09

## 更新内容

已将 **GPT 模型配置格式统一为 Claude 格式**，并添加了最新的 **GPT-6 系列**和 **GPT-6.1 Sol** 模型。

## 新增模型

### GPT-6 系列（2026年9月发布）

#### 1. GPT-6 Astra
- **模型 ID**: `openai.gpt-6-astra`
- **发布日期**: 2026-09-08
- **特点**: OpenAI 最强大的模型，适合最复杂的端到端工作
- **用途**: 复杂推理、编程、计算机使用、研究、文档创建
- **上下文**: 1,050,000 tokens
- **输出**: 最多 128,000 tokens
- **Inference Profiles**:
  - US: `us.openai.gpt-6-astra`
  - Global: `global.openai.gpt-6-astra`

#### 2. GPT-6 Sol
- **模型 ID**: `openai.gpt-6-sol`
- **发布日期**: 2026-09-22
- **特点**: 为要求苛刻的开发工作设计
- **用途**: 构建功能、调试重构代码、代码审查、多步骤工作
- **上下文**: 1,050,000 tokens
- **输出**: 最多 128,000 tokens
- **Inference Profiles**:
  - US: `us.openai.gpt-6-sol`
  - Global: `global.openai.gpt-6-sol`

#### 3. GPT-6 Luna
- **模型 ID**: `openai.gpt-6-luna`
- **发布日期**: 2026-09-22
- **特点**: 平衡智能、速度和成本
- **用途**: 日常工作、高频任务
- **上下文**: 1,050,000 tokens
- **输出**: 最多 128,000 tokens
- **Inference Profiles**:
  - US: `us.openai.gpt-6-luna`
  - Global: `global.openai.gpt-6-luna`

#### 4. GPT-6.1 Sol
- **模型 ID**: `openai.gpt-6-1-sol`
- **特点**: 接近 GPT-6 Astra 的性能，Sol 的价格
- **用途**: 编程、专业工作、代理工作流
- **Inference Profiles**:
  - US: `us.openai.gpt-6-1-sol`
  - Global: `global.openai.gpt-6-1-sol`

## 格式统一

### 修改前
```python
GPT_MODELS = [
    {"id": "openai.gpt-6", "label": "GPT-6", "series": "gpt-6", "quota_key": "gpt-6"},
    # ...
]
```

### 修改后（与 Claude 格式一致）
```python
GPT_MODELS = [
    {
        "id": "openai.gpt-6-astra",
        "label": "GPT-6 Astra",
        "series": "gpt-6",
        "quota_key": "gpt-6 astra",
        "sources": {
            "us": "us.openai.gpt-6-astra",
            "global": "global.openai.gpt-6-astra",
        },
    },
    # ...
]
```

### 统一的字段
- `id`: Bedrock Foundation Model ID
- `label`: 显示名称
- `series`: 模型系列（用于分组）
- `quota_key`: AWS Service Quotas 配额关键词
- `sources`: 系统 Inference Profile ID（新增，与 Claude 一致）

## 完整模型列表

### GPT-6 系列（4个）
1. GPT-6 Astra - 最强大
2. GPT-6 Sol - 开发工作
3. GPT-6 Luna - 平衡性能
4. GPT-6.1 Sol - 高性价比

### GPT-5 系列（5个）
1. GPT-5.6 Sol
2. GPT-5.6 Terra
3. GPT-5.6 Luna
4. GPT-5.5
5. GPT-5.4

### GPT OSS 系列（4个）
1. GPT OSS 20B
2. GPT OSS 120B
3. GPT OSS Safeguard 20B
4. GPT OSS Safeguard 120B

**总计**: 13 个 GPT 模型

## 优势

### 1. 格式统一
- GPT 和 Claude 模型使用相同的数据结构
- 便于维护和扩展
- 代码逻辑更一致

### 2. 支持 Inference Profiles
- 添加了 `sources` 字段，包含系统 Inference Profile ID
- 与 Claude 模型创建流程一致
- 支持跨区域推理

### 3. 配额查询改进
- 保留了 `quota_key` 字段用于精确匹配 AWS Service Quotas
- 支持查询 GPT-6 系列的配额

## 使用方法

### API 调用
所有现有的 GPT API 端点保持不变：
- `/api/gpt/query_quotas` - 查询 GPT 配额
- `/api/gpt/accounts/list` - 列出账户
- `/api/gpt/accounts/test` - 测试 GPT 调用
- 等等

### 创建 Inference Profile
GPT 模型现在支持通过 Inference Profile 创建（与 Claude 相同）：
```python
# 可以使用 sources 中的 Inference Profile ID
# 例如: us.openai.gpt-6-astra, global.openai.gpt-6-sol
```

## 区域可用性

根据 OpenAI 和 AWS 文档：

- **GPT-6 Sol & Luna**: us-east-1 (N. Virginia) 的 Bedrock Runtime 和 Mantle
- **GPT-6 Astra**: us-west-2 (Oregon) 的 Bedrock Runtime 和 Mantle
- **GPT-5.6 系列**: us-east-2 及其他区域
- **所有模型**: 通过 US 和 Global Inference Profiles 可用

## 向后兼容性

- ✅ 所有现有功能保持不变
- ✅ 原有的模型 ID 仍然有效
- ✅ 配额查询逻辑兼容新旧格式
- ✅ 不影响已有的 GPT API 调用

## 验证结果

✓ 已通过 Python 语法检查  
✓ GPT 模型总数从 10 个增加到 13 个  
✓ 新增 GPT-6 系列 4 个模型  
✓ 格式统一为 Claude 风格  
✓ 添加了 sources 字段支持 Inference Profiles  
✓ 保留了 quota_key 用于配额查询  

## 参考资料

- [OpenAI GPT-6 Astra on Amazon Bedrock](https://aws.amazon.com/about-aws/whats-new/2026/09/openai-gpt-6-astra-on-amazon-bedrock/)
- [OpenAI GPT-6 Sol and Luna on Amazon Bedrock](https://aws.amazon.com/about-aws/whats-new/2026/09/openai-gpt-6-sol-luna-on-amazon-bedrock/)
- [OpenAI on Amazon Bedrock Guide](https://developers.openai.com/api/docs/guides/amazon-bedrock)
- [AWS Bedrock OpenAI Model Cards](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards-openai.html)

## 配额刷新建议

首次查询 GPT-6 系列配额时，建议：
1. 勾选"强制刷新配额代码"
2. 或删除 `outputs/quota_codes.json` 缓存文件
3. 让系统从 AWS 重新拉取最新的 Service Quotas

这样可以确保 GPT-6 Astra、Sol、Luna 和 GPT-6.1 Sol 的配额信息正确显示。
