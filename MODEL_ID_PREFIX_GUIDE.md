# Model ID 前缀自动添加功能说明

## 问题背景

在直接测试 Model ID 时，AWS Bedrock 要求使用 **inference profile ID** 而不是 foundation model ID。由于你主要使用 `global` inference profile，系统现在会自动在输入的 model_id 前添加 `global.` 前缀。

### AWS 错误示例
```
AWS 错误: Invocation of model ID anthropic.claude-opus-4-7 with on-demand throughput 
isn't supported. Retry your request with the ID or ARN of an inference profile 
that contains this model.
```

## 改进内容

### 后端改进（`app.py` - `test_model_id()` 函数）

**自动尝试顺序：**
1. **优先尝试 global inference profile**（如果用户输入的 ID 没有前缀）
   - 输入：`anthropic.claude-opus-4-7`
   - 尝试：`global.anthropic.claude-opus-4-7` ✓

2. **其次尝试 US 地域 inference profile**
   - 尝试：`us.anthropic.claude-opus-4-7`

3. **最后尝试原始 ID**（如果以上都不支持）
   - 尝试：`anthropic.claude-opus-4-7`

**返回信息包括：**
```json
{
  "ok": true,
  "invoke_ok": true,
  "requested_model_id": "anthropic.claude-opus-4-7",        // 用户输入的原始 ID
  "used_model_id": "global.anthropic.claude-opus-4-7",      // 实际使用的 ID
  "is_global_inference_profile": true,                       // 是否用了 global
  "prefix_applied": true,                                    // 是否应用了前缀
  "input_tokens": 10,
  "output_tokens": 25,
  "preview": "响应内容..."
}
```

### 前端改进（`test_profile.html`）

**成功时的显示：**
- 请求的 model_id（用户输入）
- 实际使用的 model_id（自动转换后）
- Profile 类型标记（✓ global 或 regional）
- 自动转换说明（黄色提示框）

**示例显示：**
```
状态: ✓ 可用
区域: us-east-1
Profile 类型: global ✓
Token 使用: in 10 / out 25

请求的 model id
anthropic.claude-opus-4-7

实际使用的 model id  
global.anthropic.claude-opus-4-7

✓ 自动添加前缀: 从 "anthropic.claude-opus-4-7" 转换为 
"global.anthropic.claude-opus-4-7" (global inference profile)
```

**失败时的显示：**
- 尝试的所有 model_id（按优先级顺序）
- 最后尝试的 ID 和具体错误
- 建议查看错误信息调试

## 使用方法

### 方式 1：使用下拉菜单选择（推荐）
1. 选择区域（如 us-east-1）
2. 从下拉菜单选择 Model ID
3. 点击"测试"按钮
4. 系统自动添加 global. 前缀并测试

**优点：**
- 简单快速
- 自动处理所有转换

### 方式 2：自定义输入 Model ID
1. 在"自定义 model id"输入框输入 model_id
2. 可以输入以下任意格式：
   - Foundation model ID: `anthropic.claude-opus-4-7`
   - Global inference profile: `global.anthropic.claude-sonnet-5`
   - US inference profile: `us.anthropic.claude-opus-5`
   - 完整 ARN: `arn:aws:bedrock:us-east-1:123456789012:inference-profile/xxx`

3. 点击"测试"按钮

**系统处理逻辑：**
- 如果输入没有前缀且不是 ARN，自动尝试 global.xxx
- 如果输入已有前缀（global.、us. 等），直接使用
- 如果输入是完整 ARN，直接使用

## 示例场景

### 场景 1：测试基础 Model ID（最常见）
**用户输入：**
```
模型: Claude Opus 5
自定义输入: anthropic.claude-opus-5
```

**系统尝试：**
1. ✓ 尝试 `global.anthropic.claude-opus-5` → 成功！

**返回信息：**
```
✓ 自动添加前缀: 从 "anthropic.claude-opus-5" 转换为 
"global.anthropic.claude-opus-5" (global inference profile)
```

### 场景 2：已经有前缀
**用户输入：**
```
自定义输入: global.anthropic.claude-sonnet-4-5
```

**系统尝试：**
1. ✓ 直接尝试 `global.anthropic.claude-sonnet-4-5` → 成功！

**返回信息：**
```
状态: ✓ 可用（无前缀提示，已正确格式）
```

### 场景 3：模型不可用
**用户输入：**
```
自定义输入: anthropic.claude-old-version
```

**系统尝试：**
1. ✗ 尝试 `global.anthropic.claude-old-version` → 失败
2. ✗ 尝试 `us.anthropic.claude-old-version` → 失败
3. ✗ 尝试 `anthropic.claude-old-version` → 失败

**返回信息：**
```
✗ 不可用

尝试的 model id（优先级顺序）:
- global.anthropic.claude-old-version
- us.anthropic.claude-old-version
- anthropic.claude-old-version

错误: Model not found or unsupported
```

## 技术实现细节

### 后端代码流程
```python
# 1. 准备候选 model_id 列表
candidates = []

# 2. 如果没有前缀，优先添加 global
if not has_prefix:
    candidates.append(("global." + model_id, is_global=True))

# 3. 添加原始 ID
candidates.append((model_id, is_global=False))

# 4. 尝试每个候选，直到成功
for candidate_id in candidates:
    try:
        response = bedrock_runtime.converse(modelId=candidate_id, ...)
        return success(candidate_id)  # 第一个成功的即可
    except ClientError:
        continue  # 尝试下一个
```

### 前端显示逻辑
```javascript
if(d.prefix_applied){  // 如果系统应用了前缀
    // 显示黄色提示框解释发生了什么
    prefixBadge = `✓ 自动添加前缀: 从 "${requested}" 转换为 "${used}" (global 推理配置)`;
}
```

## 常见问题

### Q: 为什么自动加 global. 前缀？
**A:** AWS Bedrock 的 on-demand 模式不支持直接使用 foundation model ID，必须通过 inference profile。Global inference profile 在所有支持该模型的区域都可用，因此优先使用。

### Q: 如果模型在 global 不可用但在 us 可用怎么办？
**A:** 系统会自动尝试下一个候选（us.xxx），确保找到可用的配置。

### Q: 我可以禁用自动前缀添加吗？
**A:** 可以，在自定义输入框中输入完整的 ARN 或已经有前缀的 model_id 即可（系统会检测到并跳过自动添加）。

### Q: 为什么显示"尝试的 model_id"列表？
**A:** 当测试失败时，这个列表帮助你理解系统尝试的顺序和方式，便于调试和理解错误原因。

## 部署说明

### 本地测试
1. 替换 app.py（新的 test_model_id 函数）
2. 替换 templates/test_profile.html（更新的 UI）
3. 重启 Flask：`python app.py`
4. 访问 http://localhost:5000/test-profile

### EC2 部署
```bash
cd ~/app
git pull origin main
sudo systemctl restart bedrock-app
```

### 验证功能
1. 选择区域和模型
2. 点击"测试"
3. 确认显示"✓ 自动添加前缀"提示（第一次测试基础 model_id）
4. 确认 token 使用和响应正确

## 版本信息

- **功能版本:** 2.0
- **发布日期:** August 4, 2026
- **改进:** 自动前缀添加和 global inference profile 优先
- **兼容性:** 完全向后兼容，不影响现有功能

## 后续改进建议

- [ ] 根据区域自动选择最优 inference profile（global > 地域 > foundation）
- [ ] 缓存成功的 model_id 前缀组合
- [ ] 添加"学习模式"自动记录可用的组合
- [ ] Web UI 显示不同地域的可用状态

---

**有问题？** 查看完整的测试指南或检查 server 日志：
```bash
sudo journalctl -u bedrock-app -f
```
