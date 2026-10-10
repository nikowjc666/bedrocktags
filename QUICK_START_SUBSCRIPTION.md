# SSO 用户 + 订阅快速开始指南

## 🚀 5 分钟快速上手

### 第一步：启动应用

```bash
# 确保已安装依赖
pip install -r requirements.txt

# 启动 Flask 应用
python app.py
```

访问：http://localhost:5001/sso

---

### 第二步：填写 AWS 凭证

1. **Access Key ID**：你的 AWS Access Key
2. **Secret Access Key**：你的 AWS Secret Key  
3. **区域**：如 `us-east-1`
4. **Session Token**（可选）：如果使用临时凭证

点击 **"检测凭证"** 验证配置是否正确

---

### 第三步：配置用户信息

#### 基础配置
- **用户名前缀**：kiro
- **邮箱域名**：example.com  
- **数量**：3（先测试少量）
- **序号起始值**：1
- **序号位数**：2

#### SSO 配置
- **SSO 组名**：Kiro-Users
- **并发数**：8（默认即可）

**勾选选项：**
- ✅ 组不存在时自动创建

---

### 第四步：选择订阅方案 ⭐ 重点

#### 订阅配置
- **Kiro 订阅方案**：从下拉列表选择
  - 免费版（Free）
  - 专业版 - 月付（Pro Monthly）
  - 专业版 - 年付（Pro Yearly）✨ 推荐
  - 团队版 - 月付（Team Monthly）
  - 团队版 - 年付（Team Yearly）
  - 企业版（Enterprise）

- **订阅有效期**：365 天（默认一年）

**勾选选项：**
- ✅ 自动为所有用户分配订阅

---

### 第五步：执行创建

1. 点击 **"预览"** 查看将要创建的用户列表
2. 确认无误后，点击 **"开始执行（创建 + 生成密码 + 分配订阅）"**
3. 观察实时进度：
   - ✅ 已创建：新建的用户数
   - ⚠️ 已跳过：已存在的用户数
   - ❌ 失败：创建失败的用户数
   - 🔑 已生成密码：成功生成密码的数量
   - 📦 **已分配订阅**：成功分配订阅的数量 ⭐

---

### 第六步：查看结果

#### 在线查看
- 结果表格显示每个用户的详细信息
- 点击 **"查看已有订阅"** 验证订阅分配情况

#### 导出文件
- **导出 TXT**：纯文本格式，方便打印
- **导出 CSV**：表格格式，可用 Excel 打开

---

## 📋 示例配置

### 场景 1：创建 5 个专业版年付用户

```
用户名前缀：kiro
邮箱域名：mycompany.com
数量：5
订阅方案：专业版 - 年付（Pro Yearly）
订阅有效期：365 天
```

**结果：**
- kiro01@mycompany.com ✓ Pro Yearly
- kiro02@mycompany.com ✓ Pro Yearly
- kiro03@mycompany.com ✓ Pro Yearly
- kiro04@mycompany.com ✓ Pro Yearly
- kiro05@mycompany.com ✓ Pro Yearly

---

### 场景 2：创建 10 个团队版月付用户

```
用户名前缀：team
邮箱域名：startup.io
数量：10
序号起始值：1
订阅方案：团队版 - 月付（Team Monthly）
订阅有效期：30 天
```

**结果：**
- team01@startup.io ✓ Team Monthly
- team02@startup.io ✓ Team Monthly
- ...
- team10@startup.io ✓ Team Monthly

---

## 🔍 验证订阅

### 方法 1：界面查看
点击 **"查看已有订阅"** 按钮，弹出订阅列表

### 方法 2：测试脚本
```bash
python test_subscription.py
```

### 方法 3：直接查询数据库
```bash
sqlite3 users.db "SELECT email, plan, start_date, end_date FROM subscriptions;"
```

---

## ⚠️ 常见问题

### Q1: 订阅分配失败怎么办？

**检查项：**
1. 确认勾选了"自动为所有用户分配订阅"
2. 确认选择了订阅方案（不能为空）
3. 查看错误信息，可能是数据库权限问题

**解决方案：**
- 用户创建成功，订阅可以后续补分配
- 或者重新执行一次（已存在的用户会跳过）

---

### Q2: 如何修改已有用户的订阅？

**方法 1：数据库直接修改**
```bash
sqlite3 users.db
UPDATE subscriptions SET plan='pro_yearly' WHERE email='kiro01@example.com';
```

**方法 2：重新执行**
设置相同的用户名和邮箱，系统会更新订阅信息

---

### Q3: 如何延长订阅有效期？

```bash
sqlite3 users.db
UPDATE subscriptions 
SET end_date=datetime(end_date, '+365 days') 
WHERE email='kiro01@example.com';
```

---

### Q4: 订阅数据存在哪里？

- **开发/测试环境**：本地 SQLite 数据库 `users.db`
- **生产环境**：需要集成实际的 Kiro 订阅系统 API

---

## 🎯 最佳实践

### 1. 先小规模测试
- 首次使用建议创建 **2-3 个用户**
- 验证功能正常后再批量创建

### 2. 统一命名规范
- 用户名前缀建议使用统一的标识
- 例如：`kiro_dev`、`kiro_prod`、`team_2024`

### 3. 记录创建信息
- 每次批量创建后导出 CSV 文件
- 建立用户档案，方便后续管理

### 4. 定期检查订阅状态
- 使用"查看已有订阅"功能定期核对
- 注意订阅到期时间，及时续期

### 5. 合理设置并发数
- **小批量（< 10 个）**：并发数 4-8
- **中批量（10-50 个）**：并发数 8-12
- **大批量（> 50 个）**：并发数 12-16

---

## 📊 导出文件示例

### TXT 格式示例
```
默认 AWS access portal URL: https://d-9xxxxxxxxx.awsapps.com/start
双栈 AWS access portal URL: https://ssoins-xxx.portal.us-east-1.app.aws
用户名: kiro01
一次性密码: TempPass@123
Kiro 订阅方案: pro_yearly

用户名: kiro02
一次性密码: TempPass@456
Kiro 订阅方案: pro_yearly
...
```

### CSV 格式示例
```csv
username,email,portal_url,dualstack_url,one_time_password,subscription_plan,group,status
kiro01,kiro01@example.com,https://...,https://...,TempPass@123,pro_yearly,Kiro-Users,已创建 / 已加入组 Kiro-Users / 已分配订阅 pro_yearly
kiro02,kiro02@example.com,https://...,https://...,TempPass@456,pro_yearly,Kiro-Users,已创建 / 已加入组 Kiro-Users / 已分配订阅 pro_yearly
```

---

## 🔗 相关文档

- [详细升级说明](./SSO_SUBSCRIPTION_UPGRADE.md)
- [SSO 用户生成器](./sso_user_generator.py)
- [测试脚本](./test_subscription.py)

---

## 💡 下一步

1. **集成生产环境**
   - 将 `assign_subscription_to_user` 函数连接到实际 Kiro API
   - 配置生产数据库连接

2. **增强功能**
   - 添加订阅修改功能
   - 添加订阅续期功能
   - 添加批量取消订阅

3. **监控和告警**
   - 订阅即将到期提醒
   - 订阅使用统计报表
   - 异常订阅检测

---

**祝使用愉快！** 🎉

有问题随时联系开发团队。
