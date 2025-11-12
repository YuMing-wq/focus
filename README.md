# 音频转录和总结工具

一个Web应用，用于对音频文件进行文本提取和智能总结，并支持基于转录内容的智能对话。使用OpenAI的Whisper API进行音频转录，使用GPT-4o-mini模型进行文本总结，集成LangChain框架实现RAG问答功能，支持流式输出。

## ✨ 功能特性

- 🎤 **音频转录**: 使用OpenAI Whisper API将音频文件转换为文本
- 📝 **智能总结**: 使用GPT-4o-mini模型对转录文本进行总结
- 💬 **智能对话**: 基于音频转录内容进行问答对话（使用LangChain）
- 🧠 **上下文理解**: 使用RAG技术，模型能准确回答关于转录内容的问题
- 🌊 **流式输出**: 实时显示转录、总结和对话结果，提供流畅的用户体验
- 🎨 **现代UI**: 简洁美观的前端界面，支持拖拽上传
- 🚀 **Web界面**: 通过浏览器轻松使用，无需命令行操作

## 🏗️ 项目结构

```
focus/
├── app.py                 # FastAPI后端服务
├── index.html            # 前端页面
├── main.py               # 命令行版本（保留）
├── start.py              # 快速启动脚本
├── requirements.txt      # Python依赖
├── .env.example          # 环境变量示例文件
└── README.md            # 项目文档
```

## 📋 系统要求

- Python 3.8 或更高版本
- 现代浏览器（Chrome、Firefox、Edge等）
- OpenAI API密钥

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

> **注意**: 你需要从 [OpenAI官网](https://platform.openai.com/api-keys) 获取API密钥。

### 3. 启动应用

#### 快速启动（推荐）

使用启动脚本同时启动前后端服务：

```bash
python start.py
```

#### 手动启动

**启动后端服务：**
```bash
python app.py
```

或者使用 uvicorn：

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

**启动前端服务：**
```bash
# 使用Python内置服务器
python -m http.server 8080
```

### 4. 访问应用

- 后端API: `http://localhost:8000`
- 前端界面: `http://localhost:8080`

在浏览器中打开 `http://localhost:8080` 即可使用应用。

### 5. 使用应用

1. 打开前端页面
2. 点击上传区域或拖拽音频文件到上传区域
3. 点击"开始处理"按钮
4. 实时查看转录和总结结果（流式输出）
5. 转录完成后，在对话区域输入问题
6. 模型会基于转录内容进行智能回答

## 🛠️ 技术栈

### 后端

- **FastAPI**: 现代化的Python Web框架，支持异步和流式响应
- **OpenAI API**: Whisper和GPT-4o-mini模型
- **LangChain**: 构建基于LLM的应用框架，实现RAG功能
- **FAISS**: Facebook开源的向量数据库，用于高效检索
- **SSE**: Server-Sent Events实现流式输出

### 前端

- **原生HTML/CSS/JavaScript**: 无需构建工具，直接运行
- **Fetch API**: 处理文件上传和SSE流式响应
- **现代CSS**: 渐变背景和流畅动画效果

## 📡 API接口

### GET `/`

返回API信息。

### POST `/process`

处理音频文件，返回转录结果（不含总结）。

**请求:**
- Content-Type: `multipart/form-data`
- Body: `file` (音频文件)

**响应:**
```json
{
  "status": "success",
  "transcription": "转录的文本内容",
  "filename": "文件名"
}
```

### POST `/process-with-summary`

处理音频文件，返回流式响应（包含转录、总结和会话ID）。

**请求:**
- Content-Type: `multipart/form-data`
- Body: `file` (音频文件)

**响应:**
- Content-Type: `text/event-stream`
- SSE事件类型:
  - `status`: 状态更新
  - `transcription`: 转录结果
  - `summary_chunk`: 总结片段（流式）
  - `session_created`: 会话创建成功（包含session_id）
  - `complete`: 处理完成
  - `error`: 错误信息

### POST `/chat`

基于转录文本的对话接口（流式响应）。

**请求:**
- Content-Type: `application/json`
- Body:
```json
{
  "session_id": "会话ID",
  "message": "用户问题"
}
```

**响应:**
- Content-Type: `text/event-stream`
- SSE事件类型:
  - `status`: 状态更新
  - `chat_chunk`: 回答片段（流式）
  - `complete`: 回答完成
  - `error`: 错误信息

### GET `/session/{session_id}`

获取会话信息。

**响应:**
```json
{
  "session_id": "会话ID",
  "transcription": "转录文本",
  "chat_history_count": 2
}
```

## 💻 命令行版本

项目还保留了命令行版本，可以直接使用：

```bash
python main.py audio.mp3
```

## 📝 注意事项

1. **API费用**: 使用OpenAI API会产生费用，请查看 [OpenAI定价页面](https://openai.com/api/pricing/) 了解详情
2. **文件大小**: 音频文件大小限制取决于OpenAI API的限制（通常为25MB）
3. **网络连接**: 需要稳定的网络连接才能调用API
4. **API密钥安全**: 请妥善保管你的API密钥，不要将其提交到代码仓库

## 🐛 故障排除

### 后端启动失败

- 检查Python版本是否符合要求
- 确认所有依赖已正确安装
- 检查 `.env` 文件是否存在且包含有效的API密钥

### 前端无法连接后端

- 确认后端服务正在运行（`http://localhost:8000`）
- 检查 `index.html` 中的 `API_BASE_URL` 配置是否正确
- 如果使用文件协议打开HTML，需要使用HTTP服务器
- 查看浏览器控制台的错误信息

### 流式输出不工作

- 检查网络连接
- 查看后端日志中的错误信息
- 确认OpenAI API密钥有效且有足够余额

### 音频上传失败

- 检查文件格式是否支持
- 确认文件大小未超过限制
- 查看后端日志获取详细错误信息

## 📄 许可证

本项目仅供学习和个人使用。

## 🤝 贡献

欢迎提交问题和改进建议！

## 🔄 更新日志

### v3.0.0
- ✨ 集成LangChain框架，实现智能对话功能
- ✨ 支持基于转录文本的问答对话
- ✨ 使用RAG技术实现上下文检索
- ✨ 会话管理和历史记录功能
- ✨ 对话界面支持流式输出
- 🔧 添加FAISS向量数据库支持

### v2.0.0
- ✨ 添加Web界面，支持文件上传
- ✨ 实现流式输出功能
- ✨ 全新的现代化前端界面
- ✨ 支持拖拽上传文件

### v1.0.0
- 🎉 初始版本
- ✨ 支持音频转录和文本总结功能
- ✨ 命令行版本
