# 405 Method Not Allowed 错误修复日志

## 问题描述

在使用 `python start.py` 启动应用并上传音频文件时，出现以下网络连接错误：

```
INFO: 127.0.0.1:54723 - "GET /process-with-summary HTTP/1.1" 405 Method Not Allowed
INFO: 127.0.0.1:52082 - "POST /process-with-summary HTTP/1.1" 200 OK
INFO: 127.0.0.1:61562 - "GET /process-with-summary HTTP/1.1" 405 Method Not Allowed
```

## 问题分析

问题的根本原因是前端使用了 `EventSource` 来建立SSE（Server-Sent Events）连接，但 `EventSource` 只支持 GET 请求，而我们的 `/process-with-summary` API端点需要 POST 请求（因为需要上传文件）。

前端代码中存在以下逻辑：
1. 使用 `EventSource` 连接 `/process-with-summary`（发送 GET 请求）
2. 服务器返回 405 Method Not Allowed
3. 同时发送 POST 请求处理文件上传，成功返回 200 OK

## 解决方案

修改前端代码（`index.html`），将 `EventSource` 替换为使用 `fetch` API 来发送 POST 请求并处理流式响应：

### 修改前（有问题的代码）
```javascript
// 发起SSE请求
eventSource = new EventSource(`${API_BASE_URL}/process-with-summary`);

// 发送文件
const response = await fetch(`${API_BASE_URL}/process-with-summary`, {
    method: 'POST',
    body: formData
});
```

### 修改后（修复的代码）
```javascript
// 发送POST请求并处理流式响应
const response = await fetch(`${API_BASE_URL}/process-with-summary`, {
    method: 'POST',
    body: formData
});

// 处理流式响应
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            // 处理不同的消息类型...
        }
    }
}
```

## 验证修复

运行测试脚本验证修复效果：

```bash
python test_fix.py
```

输出结果：
- ✅ GET /process-with-summary 返回 405 Method Not Allowed
- ✅ POST /process-with-summary 正确处理POST请求
- ✅ 前端不再发送错误的GET请求

## 修复后的优势

1. **消除405错误**：不再发送无效的GET请求
2. **更高效**：直接使用POST请求处理文件上传和流式响应
3. **更好的兼容性**：使用原生fetch API，更广泛的浏览器支持
4. **实时流式显示**：保持了原有的流式输出功能

## 使用方法

修复后，使用方法不变：

1. 配置环境变量（创建 `.env` 文件）
2. 运行 `python start.py`
3. 在浏览器访问 `http://localhost:8080`
4. 上传音频文件，查看转录和总结结果

现在应用应该正常工作，不再出现405错误。
