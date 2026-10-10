# 模型配置总结

## 更新概览

本次更新统一了 Claude 和 GPT 模型的配置格式，并添加了最新模型。

## Claude 模型（16个）

### Claude 5 系列
| 模型 | ID | 区域 | 状态 |
|------|----|----|------|
| Claude Opus 5.5 | anthropic.claude-opus-5-5 | US, EU, Global | ✓ |
| Claude Sonnet 5.5 | anthropic.claude-sonnet-5-5 | US, EU, Global | ✓ |
| Claude Haiku 5.5 | anthropic.claude-haiku-5-5 | US, EU, Global | ✅ 新增 |
| Claude Sonnet 5 | anthropic.claude-sonnet-5 | US, Global | ✓ |
| Claude Fable 5.1 | anthropic.claude-fable-5-1 | US, EU, Global | ✓ |
| Claude Fable 5 | anthropic.claude-fable-5 | US, EU, Global | ✓ |
| Claude Opus 5 | anthropic.claude-opus-5 | US, EU, Global | ✓ |

### Claude 4 系列
| 模型 | ID | 区域 | 状态 |
|------|----|----|------|
| Claude Opus 4.8 | anthropic.claude-opus-4-8 | US, EU, JP, AU, Global | ✓ |
| Claude Opus 4.7 | anthropic.claude-opus-4-7 | Global | ✓ |
| Claude Opus 4.6 | anthropic.claude-opus-4-6-v1 | US, EU, Global | ✓ |
| Claude Sonnet 4.6 | anthropic.claude-sonnet-4-6 | US, EU, Global | ✓ |
| Claude Sonnet 4.5 | anthropic.claude-sonnet-4-5-20250929-v1:0 | US, EU, Global | ✓ |
| Claude Haiku 4.5 | anthropic.claude-haiku-4-5-20251001-v1:0 | US, EU, Global | ✓ |
| Claude Opus 4.5 | anthropic.claude-opus-4-5-20251101-v1:0 | US, EU, Global | ✓ |
| Claude Opus 4 | anthropic.claude-opus-4-20250514-v1:0 | US, EU, Global | ✓ |
| Claude Sonnet 4 | anthropic.claude-sonnet-4-20250514-v1:0 | US, EU, Global | ✓ |

## GPT 模型（13个）

### GPT-6 系列
| 模型 | ID | 区域 | 状态 |
|------|----|----|------|
| GPT-6 Astra | openai.gpt-6-astra | US, Global | ✅ 新增 |
| GPT-6 Sol | openai.gpt-6-sol | US, Global | ✅ 新增 |
| GPT-6 Luna | openai.gpt-6-luna | US, Global | ✅ 新增 |
| GPT-6.1 Sol | openai.gpt-6-1-sol | US, Global | ✅ 新增 |

### GPT-5 系列
| 模型 | ID | 区域 | 状态 |
|------|----|----|------|
| GPT-5.6 Sol | openai.gpt-5-6-sol | US, Global | ✓ |
| GPT-5.6 Terra | openai.gpt-5-6-terra | US, Global | ✓ |
| GPT-5.6 Luna | openai.gpt-5-6-luna | US, Global | ✓ |
| GPT-5.5 | openai.gpt-5-5 | US, Global | ✓ |
| GPT-5.4 | openai.gpt-5-4 | US, Global | ✓ |

### GPT OSS 系列
| 模型 | ID | 区域 | 状态 |
|------|----|----|------|
| GPT OSS 20B | openai.gpt-oss-20b-1:0 | - | ✓ |
| GPT OSS 120B | openai.gpt-oss-120b-1:0 | - | ✓ |
| GPT OSS Safeguard 20B | openai.gpt-oss-safeguard-20b | - | ✓ |
| GPT OSS Safeguard 120B | openai.gpt-oss-safeguard-120b | - | ✓ |

## 统计

- **Claude 模型总数**: 16 个（新增 1 个）
- **GPT 模型总数**: 13 个（新增 4 个）
- **模型总数**: 29 个

## 格式统一

### 统一的字段结构
```python
{
    "id": "模型ID",          # Bedrock Foundation Model ID
    "label": "显示名称",      # 用户界面显示
    "series": "系列",        # GPT: gpt-6/gpt-5/gpt-oss
    "quota_key": "配额键",   # GPT: 用于配额查询
    "sources": {            # 系统 Inference Profile ID
        "us": "us.xxx",
        "eu": "eu.xxx",     # Claude 专有
        "global": "global.xxx",
    }
}
```

### Claude 特有字段
- 更多区域支持（EU, JP, AU）
- 使用 `label` 而非 `quota_key`

### GPT 特有字段
- `series` 字段用于分组
- `quota_key` 精确匹配 AWS Service Quotas
- 较少的区域（主要是 US 和 Global）

## 配额支持

所有模型都支持通过 AWS Service Quotas 查询 TPM/TPD：
- ✅ Claude 模型：通过 label 生成配额名称变体
- ✅ GPT 模型：通过 quota_key 精确匹配

## 发布时间线

```
2026-06 ─── GPT-5.5, GPT-5.4 发布
2026-07 ─── GPT-5.6 系列（Sol, Terra, Luna）发布
2026-09 ─── GPT-6 Astra 发布（09-08）
2026-09 ─── GPT-6 Sol, Luna 发布（09-22）
2026-10 ─── Claude Haiku 5.5 发布（10-07）
2026-10 ─── 本次系统更新（10-09）
```

## 使用建议

### 首次查询新模型配额
1. 勾选"强制刷新配额代码"
2. 或删除 `outputs/quota_codes.json`
3. 让系统从 AWS 重新拉取配额

### 选择模型
- **最强性能**: Claude Opus 5.5, GPT-6 Astra
- **平衡选择**: Claude Sonnet 5.5, GPT-6 Sol
- **高性价比**: Claude Haiku 5.5, GPT-6 Luna
- **开发工作**: GPT-6 Sol, GPT-6.1 Sol

## 相关文档
- `HAIKU_55_UPDATE.md` - Claude Haiku 5.5 详细说明
- `GPT_MODELS_UPDATE.md` - GPT 模型更新详细说明
