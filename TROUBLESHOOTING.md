# 故障排查指南 - 对话功能404错误

## 问题描述

当音频转录完成后，用户尝试提问时前端显示：**"发送失败: HTTP 404: Not Found"**

## 可能的原因

### 1. 会话未成功创建

**症状**: 转录完成但会话实际上未创建

**原因**:
- OpenAI API密钥未配置或无效
- 创建向量存储时失败（需要调用OpenAI Embeddings API）
- 网络连接问题

**解决方法**:
```bash
# 检查.env文件
cat .env  # 或在Windows上: type .env

# 应该包含有效的API密钥
OPENAI_API_KEY=sk-xxxxxxxxxxxxx

# 运行诊断脚本
python diagnose.py
```

### 2. 会话被过期清理

**症状**: 会话创建成功但在发送消息前已被清理

**原因**:
- 会话超时（默认1小时未使用）
- 服务器重启导致内存中的会话丢失

**解决方法**:
- 转录完成后尽快提问
- 重新上传音频文件创建新会话

### 3. 会话ID不匹配

**症状**: 前端保存的session_id与后端不一致

**原因**:
- 前端未正确接收session_created事件
- JavaScript控制台有错误

**解决方法**:
```javascript
// 打开浏览器控制台(F12)，查看是否有:
// "会话创建成功: xxxxx"
// "Session verified: {...}"
```

## 诊断步骤

### 步骤1: 运行诊断脚本

```bash
python diagnose.py
```

这将检查:
- ✓ 服务器是否运行
- ✓ API密钥是否配置
- ✓ 当前活动会话
- ✓ 错误处理是否正常

### 步骤2: 检查服务器日志

上传音频文件时，服务器应该输出:
```
Session created successfully: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

如果没有这条日志，说明会话创建失败。

### 步骤3: 检查浏览器控制台

1. 打开浏览器开发者工具 (F12)
2. 查看Console标签，寻找:
   ```
   会话创建成功: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Session verified: {...}
   ```
3. 查看Network标签，检查:
   - `/process-with-summary` 请求是否成功
   - 是否收到 `session_created` 事件
   - `/chat` 请求的payload是否包含正确的session_id

### 步骤4: 检查活动会话

访问调试端点查看当前活动会话:
```bash
curl http://localhost:8000/debug/sessions
```

或在浏览器打开: http://localhost:8000/debug/sessions

## 常见问题解决

### Q1: API密钥未配置

**错误**: 会话创建时没有任何输出

**解决**:
```bash
# 创建.env文件
echo "OPENAI_API_KEY=你的API密钥" > .env

# 重启服务器
python run_app.py
```

### Q2: 向量存储创建失败

**错误**: 服务器日志显示 "Failed to create session"

**解决**:
- 检查API密钥是否有效
- 检查API额度是否充足
- 检查网络连接是否正常

### Q3: 会话在发送消息前过期

**错误**: 转录成功但对话时提示会话不存在

**解决**:
- 转录完成后立即测试对话功能
- 检查会话超时设置（默认1小时）
- 不要重启服务器（会清空所有会话）

### Q4: 前端未收到session_created事件

**错误**: 浏览器控制台没有 "会话创建成功" 日志

**解决**:
1. 检查浏览器控制台是否有JavaScript错误
2. 确认SSE流式响应正常工作
3. 刷新页面重试

## 快速修复

如果问题仍然存在，尝试以下步骤:

```bash
# 1. 停止服务器 (Ctrl+C)

# 2. 确保.env配置正确
echo "OPENAI_API_KEY=你的真实API密钥" > .env

# 3. 重启服务器
python run_app.py

# 4. 在新终端运行诊断
python diagnose.py

# 5. 刷新浏览器页面

# 6. 上传新的音频文件

# 7. 等待转录和总结完全完成

# 8. 查看浏览器控制台确认会话创建

# 9. 尝试发送消息
```

## 验证修复

完成上述步骤后，进行验证:

1. **上传音频文件**
2. **等待转录完成** - 看到"处理完成"消息
3. **检查对话区域** - 应该显示"对话功能已就绪"
4. **查看浏览器控制台** - 应该有"Session verified"
5. **发送测试消息** - 例如"这段音频讲了什么?"
6. **等待AI回答** - 应该看到流式返回的答案

## 调试技巧

### 启用详细日志

服务器端已添加调试日志:
- 会话创建时会打印session_id
- 收到对话请求时会打印当前活动会话
- 所有错误都会被记录

### 浏览器开发者工具

- **Console**: 查看JavaScript错误和日志
- **Network**: 查看HTTP请求和响应
- **Application**: 检查本地存储和变量

### 测试API端点

```bash
# 检查服务器状态
curl http://localhost:8000/

# 查看活动会话
curl http://localhost:8000/debug/sessions

# 测试无效会话(应该返回404)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","message":"hello"}'
```

## 仍然无法解决？

如果问题依然存在:

1. 查看 `CHAT_FEATURE_GUIDE.md` 了解详细功能说明
2. 查看 `QUICK_START.md` 确认启动步骤
3. 运行 `python diagnose.py` 获取诊断报告
4. 检查服务器控制台的完整错误信息
5. 检查浏览器控制台的Network标签

## 成功标志

当一切正常工作时，你应该看到:

**服务器控制台**:
```
INFO:     Application startup complete
Session created successfully: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Chat request received - Session ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Current active sessions: ['xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx']
```

**浏览器控制台**:
```
服务器连接成功: {...}
会话创建成功: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Session verified: {session_id: "...", exists: true, ...}
Sending chat message with session_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**前端界面**:
- 转录文本正常显示
- 总结内容正常显示
- 对话区域激活并显示"对话功能已就绪"
- 可以输入和发送消息
- AI回答流式显示

