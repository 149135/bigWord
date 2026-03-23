# 🔧 AI 服务故障排查手册

## 问题现象

**错误提示**：`AI 服务暂时不可用，请检查网络或 API Key`

## 📊 问题分类及解决方案

### 1. ⚠️ 未配置 API Key

**错误信息**：`请先在"AI 助手配置"中配置 Moonshot AI API Key。`

**原因**：
- 系统未配置 Moonshot AI API Key
- 或 API Key 字段为空

**解决步骤**：
```
1. 登录系统管理后台（admin / admin123）
2. 导航至：后台管理 → AI 助手配置
3. 访问 https://platform.moonshot.cn/ 获取 API Key
4. 将 API Key 填入配置页面
5. 点击"保存配置"
6. 点击"测试连接"验证配置是否正确
```

---

### 2. 🔑 API Key 无效

**错误信息**：`❌ API Key 无效或已过期，请在"AI 助手配置"中重新配置。`

**可能原因**：
- API Key 输入错误（多余空格、缺少字符）
- API Key 已被删除或失效
- API Key 权限不足

**解决步骤**：
1. 登录 [Moonshot AI 平台](https://platform.moonshot.cn/)
2. 检查当前 API Key 状态：
   - 进入"控制台" → "API 管理"
   - 查看 Key 是否显示为"有效"
3. 如果 Key 已失效，创建新的 API Key：
   - 点击"创建 API Key"
   - 复制新生成的 Key（仅显示一次！）
4. 在系统中更新配置：
   - 后台管理 → AI 助手配置
   - 粘贴新的 API Key
   - 保存并测试

---

### 3. 🌐 网络连接问题

**错误信息**：`❌ 网络连接超时，请检查网络连接后重试。`

**可能原因**：
- 服务器无法访问外网
- 防火墙拦截
- DNS 解析失败
- 代理设置问题

**检查清单**：

#### A. 测试网络连通性
```bash
# Windows PowerShell
Test-NetConnection api.moonshot.cn -Port 443

# Linux/Mac
curl -I https://api.moonshot.cn
```

#### B. 检查防火墙规则
```bash
# Windows: 确保允许 Python 访问外网
# 控制面板 → Windows Defender 防火墙 → 允许应用通过防火墙

# Linux: 检查 iptables
sudo iptables -L -n

# 如需开放，添加规则：
sudo iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT
```

#### C. 检查代理设置
```python
# 如果服务器需要代理，在 app/app.py 中修改：
client = OpenAI(
    api_key=config.moonshot_api_key,
    base_url="https://api.moonshot.cn/v1",
    http_client=httpx.Client(
        proxies="http://your-proxy:port"  # 添加代理配置
    )
)
```

#### D. 检查 DNS
```bash
# Windows
nslookup api.moonshot.cn

# Linux/Mac
dig api.moonshot.cn
```

---

### 4. 💰 配额不足

**错误信息**：`❌ API 调用配额已用尽，请检查您的 Moonshot AI 账户余额。`

**原因**：
- 免费额度已用完
- 账户余额不足
- 达到每日/每月调用上限

**解决步骤**：
1. 登录 Moonshot AI 平台
2. 查看账户余额和使用情况：
   - 控制台 → 账户 → 余额管理
   - 控制台 → 使用统计
3. 充值账户：
   - 账户 → 充值
   - 选择充值金额完成支付
4. 或调整调用频率限制：
   - 控制台 → API 管理 → 速率限制

---

### 5. 🐛 其他异常

**错误信息**：`❌ AI 服务异常：[具体错误]。请联系管理员或在"AI 助手配置"中检查配置。`

**常见异常及处理**：

#### A. 模型不存在
```
错误：model 'xxx' not found
解决：在 AI 助手配置中选择正确的模型版本（moonshot-v1-8k）
```

#### B. 请求格式错误
```
错误：invalid request format
解决：检查系统日志，确认请求参数是否正确
```

#### C. 服务端错误 (5xx)
```
错误：internal server error
解决：这是 Moonshot AI 服务端问题，请稍后重试或联系官方支持
```

---

## 🧪 测试工具

### 在线测试连接

系统提供了内置测试功能：

1. 进入"AI 助手配置"页面
2. 点击"测试连接"按钮
3. 观察测试结果：
   - ✅ **绿色成功**：配置正确，可正常使用
   - ⚠️ **黄色警告**：配置有问题，查看具体错误信息
   - ❌ **红色错误**：网络异常或服务不可用

### 手动测试 API

使用 curl 命令测试：

```bash
curl https://api.moonshot.cn/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "moonshot-v1-8k",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

预期返回：
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "moonshot-v1-8k",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "你好！有什么我可以帮助你的吗？"
      },
      "finish_reason": "stop",
      "index": 0
    }
  ]
}
```

---

## 📝 日志分析

### 查看系统日志

查看 Flask 应用日志，定位问题：

```bash
# Windows PowerShell
Get-Content terminals\*.txt -Tail 50

# Linux/Mac
tail -f /path/to/app.log
```

### 关键日志信息

```
✅ 正常日志：
INFO: AI response received successfully

❌ 错误日志：
ERROR: AI Error: Unauthorized (401)
ERROR: AI Error: Connection timeout
ERROR: AI Error: Rate limit exceeded
```

---

## 🔄 快速重启服务

如果配置更改后仍有问题，尝试重启 Flask 服务：

```bash
# 1. 停止当前服务（Ctrl+C 或 终止进程）

# 2. 清理缓存（可选）
python -c "import sys; import os; os.system('del /S /Q __pycache__' if sys.platform == 'win32' else 'rm -rf __pycache__')"

# 3. 重启服务
python run.py
```

---

## 📞 联系支持

### Moonshot AI 官方支持

- 📧 Email: support@moonshot.cn
- 📚 文档: https://platform.moonshot.cn/docs
- 💬 社区: https://platform.moonshot.cn/community

### 系统管理员

如果以上方法都无法解决问题：

1. 收集错误信息：
   - 错误提示截图
   - 系统日志（最近 100 行）
   - 测试连接结果

2. 联系项目维护人员或在 GitHub 提交 Issue

---

## ✅ 最佳实践

### 定期维护

1. **每月检查**：
   - Moonshot AI 账户余额
   - API Key 有效性
   - 调用统计和费用

2. **每周备份**：
   - API Key（加密保存）
   - AI 配置参数

3. **监控告警**：
   - 设置余额低于 ¥10 时邮件提醒
   - API 调用失败率超过 10% 时告警

### 安全建议

1. **不要在代码中硬编码 API Key**
2. **定期轮换 API Key**（建议 3-6 个月）
3. **限制 API Key 权限范围**（仅开启必要的权限）
4. **使用环境变量或配置文件存储敏感信息**

---

## 📈 性能优化

如果 AI 响应较慢：

1. **选择合适的模型**：
   - `moonshot-v1-8k`：响应快，适合简单问答
   - `moonshot-v1-32k`：功能强，适合复杂对话

2. **优化提示词**：
   - 简洁明了，避免冗长的系统提示
   - 减少不必要的上下文信息

3. **设置超时时间**：
   ```python
   completion = client.chat.completions.create(
       model=config.ai_model,
       messages=messages,
       temperature=0.3,
       timeout=10  # 10秒超时
   )
   ```

---

✅ **配置完成后，您的 AI 服务应该可以稳定运行！**



