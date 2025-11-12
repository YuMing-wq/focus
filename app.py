#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频转录和总结Web服务
使用FastAPI构建，支持文件上传和流式响应
支持基于转录文本的对话功能
"""

import os
import asyncio
import json
import uuid
from typing import Optional, Dict, List
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# Langchain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage


# 加载环境变量
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("未找到 OPENAI_API_KEY 环境变量，请创建 .env 文件")

# 初始化OpenAI客户端
client = OpenAI(api_key=API_KEY)

# 会话存储
# 存储格式: {session_id: {transcription: str, vectorstore: FAISS, chat_history: List, last_access: datetime}}
sessions: Dict[str, Dict] = {}

# 历史记录配置
HISTORY_DIR = Path("audio_history")
HISTORY_FILE = HISTORY_DIR / "history.json"
AUDIO_FILES_DIR = HISTORY_DIR / "audio_files"

# 确保历史记录目录存在
HISTORY_DIR.mkdir(exist_ok=True)
AUDIO_FILES_DIR.mkdir(exist_ok=True)

# Pydantic模型
class ChatRequest(BaseModel):
    session_id: str
    message: str
    
class SessionResponse(BaseModel):
    session_id: str
    transcription: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("启动音频转录和总结服务")
    yield
    print("关闭服务")


# 创建FastAPI应用
app = FastAPI(
    title="音频转录和总结API",
    description="使用OpenAI Whisper和GPT-4o-mini进行音频转录和智能总结",
    version="2.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_history() -> List[Dict]:
    """加载历史记录"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            return []
    return []


def save_history(history: List[Dict]):
    """保存历史记录"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")


def add_history_record(session_id: str, filename: str, transcription: str, summary: str):
    """添加历史记录"""
    history = load_history()
    record = {
        "session_id": session_id,
        "filename": filename,
        "upload_time": datetime.now().isoformat(),
        "transcription": transcription,
        "summary": summary,
        "chat_history": []  # 初始化空的对话历史
    }
    history.insert(0, record)  # 新记录插入开头
    save_history(history)
    print(f"History record added: {session_id}")


def update_chat_history(session_id: str, chat_history: List):
    """更新会话的对话历史"""
    history = load_history()
    for record in history:
        if record["session_id"] == session_id:
            # 将消息对象转换为可序列化的字典
            serializable_history = []
            for msg in chat_history:
                if isinstance(msg, (HumanMessage, AIMessage)):
                    serializable_history.append({
                        "type": msg.__class__.__name__,
                        "content": msg.content
                    })
            record["chat_history"] = serializable_history
            save_history(history)
            print(f"Chat history updated for session: {session_id}")
            return True
    return False


def delete_history_record(session_id: str):
    """删除历史记录"""
    history = load_history()
    original_len = len(history)
    history = [r for r in history if r["session_id"] != session_id]
    if len(history) < original_len:
        save_history(history)
        print(f"History record deleted: {session_id}")
        return True
    return False


def cleanup_old_sessions():
    """清理超过1小时未使用的会话"""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, session_data in sessions.items():
        if current_time - session_data["last_access"] > timedelta(hours=1):
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del sessions[session_id]
    
    if expired_sessions:
        print(f"清理了 {len(expired_sessions)} 个过期会话")


def create_vectorstore_from_text(text: str):
    """从文本创建向量存储"""
    # 分割文本
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    
    # 创建embeddings和向量存储
    embeddings = OpenAIEmbeddings(openai_api_key=API_KEY)
    vectorstore = FAISS.from_texts(chunks, embeddings)
    
    return vectorstore


def get_or_create_session(session_id: str, transcription: str = None):
    """获取或创建会话"""
    cleanup_old_sessions()
    
    if session_id not in sessions:
        if not transcription:
            raise ValueError("创建新会话时需要提供转录文本")
        
        # 创建向量存储
        vectorstore = create_vectorstore_from_text(transcription)
        
        sessions[session_id] = {
            "transcription": transcription,
            "vectorstore": vectorstore,
            "chat_history": [],  # 存储对话历史
            "last_access": datetime.now()
        }
    else:
        # 更新最后访问时间
        sessions[session_id]["last_access"] = datetime.now()
    
    return sessions[session_id]


async def transcribe_audio_async(audio_data: bytes, filename: str) -> str:
    """
    异步转录音频文件

    Args:
        audio_data: 音频文件数据
        filename: 文件名

    Returns:
        转录的文本内容
    """
    try:
        # 将字节数据保存为临时文件
        temp_path = f"temp_{filename}"
        with open(temp_path, "wb") as f:
            f.write(audio_data)

        # 使用Whisper API转录
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        # 删除临时文件
        os.remove(temp_path)

        return transcript
    except Exception as e:
        # 确保临时文件被删除
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e


async def summarize_text_stream(text: str):
    """
    流式总结文本

    Args:
        text: 需要总结的文本

    Yields:
        SSE事件数据
    """
    try:
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的文本总结助手。请对用户提供的文本进行简洁、准确的总结，突出关键信息和要点。"
                },
                {
                    "role": "user",
                    "content": f"请总结以下文本内容：\n\n{text}"
                }
            ],
            temperature=0.7,
            max_tokens=1000,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                yield f"data: {json.dumps({'type': 'summary_chunk', 'content': content})}\n\n"
                await asyncio.sleep(0.01)  # 小延迟以确保流式输出

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'总结失败: {str(e)}'})}\n\n"


@app.get("/")
async def root():
    """API根路径，返回服务信息"""
    return {
        "name": "音频转录和总结API",
        "version": "3.0.0",
        "description": "使用OpenAI Whisper和GPT-4o-mini进行音频转录和智能总结，支持对话功能",
        "endpoints": {
            "GET /": "API信息",
            "POST /process": "音频转录（不含总结）",
            "POST /process-with-summary": "音频转录和流式总结",
            "POST /chat": "基于转录文本的对话",
            "GET /session/{session_id}": "获取会话信息"
        }
    }


@app.post("/process")
async def process_audio(file: UploadFile = File(...)):
    """
    处理音频文件，返回转录结果（不含总结）

    Args:
        file: 上传的音频文件

    Returns:
        JSON响应包含转录结果
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    # 检查文件类型
    allowed_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}。支持的格式: {', '.join(allowed_extensions)}"
        )

    try:
        # 读取文件内容
        audio_data = await file.read()

        # 检查文件大小（OpenAI限制为25MB）
        max_size = 25 * 1024 * 1024  # 25MB
        if len(audio_data) > max_size:
            raise HTTPException(status_code=400, detail="文件大小超过25MB限制")

        # 转录音频
        transcribed_text = await transcribe_audio_async(audio_data, file.filename)

        return JSONResponse({
            "status": "success",
            "transcription": transcribed_text,
            "filename": file.filename
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/process-with-summary")
async def process_audio_with_summary(file: UploadFile = File(...)):
    """
    处理音频文件，返回流式响应（包含转录和总结）

    Args:
        file: 上传的音频文件

    Returns:
        SSE流式响应
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    # 检查文件类型
    allowed_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的文件格式")

    try:
        # 读取文件内容
        audio_data = await file.read()

        # 检查文件大小
        max_size = 25 * 1024 * 1024  # 25MB
        if len(audio_data) > max_size:
            raise HTTPException(status_code=400, detail="文件大小超过25MB限制")

        async def generate_events():
            try:
                # 发送开始处理状态
                yield f"data: {json.dumps({'type': 'status', 'message': '开始处理音频文件...'})}\n\n"

                # 转录音频
                yield f"data: {json.dumps({'type': 'status', 'message': '正在转录音频...'})}\n\n"
                transcribed_text = await transcribe_audio_async(audio_data, file.filename)

                # 发送转录结果
                yield f"data: {json.dumps({'type': 'transcription', 'content': transcribed_text})}\n\n"

                # 开始总结
                yield f"data: {json.dumps({'type': 'status', 'message': '正在生成总结...'})}\n\n"

                # 收集总结内容
                summary_text = ""
                async for summary_event in summarize_text_stream(transcribed_text):
                    yield summary_event
                    # 提取总结内容
                    if summary_event.startswith('data: '):
                        try:
                            data = json.loads(summary_event[6:])
                            if data.get('type') == 'summary_chunk':
                                summary_text += data.get('content', '')
                        except:
                            pass

                # 创建会话ID
                session_id = str(uuid.uuid4())
                
                # 创建会话（包含转录文本的向量存储）
                yield f"data: {json.dumps({'type': 'status', 'message': 'Preparing chat...'}, ensure_ascii=False)}\n\n"
                try:
                    get_or_create_session(session_id, transcribed_text)
                    # 验证会话是否真的创建成功
                    if session_id in sessions:
                        yield f"data: {json.dumps({'type': 'session_created', 'session_id': session_id})}\n\n"
                        print(f"Session created successfully: {session_id}")
                        
                        # 保存到历史记录
                        add_history_record(session_id, file.filename, transcribed_text, summary_text)
                    else:
                        raise Exception("Session creation verification failed")
                except Exception as e:
                    error_msg = f"Failed to create session: {str(e)}"
                    print(error_msg)
                    yield f"data: {json.dumps({'type': 'warning', 'message': 'Chat function initialization failed'})}\n\n"

                # 发送完成状态
                yield f"data: {json.dumps({'type': 'complete', 'filename': file.filename})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            generate_events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/api/history")
async def get_history():
    """获取所有历史记录"""
    try:
        history = load_history()
        # 只返回列表信息，不返回完整内容
        history_list = [
            {
                "session_id": record["session_id"],
                "filename": record["filename"],
                "upload_time": record["upload_time"],
                "transcription_preview": record["transcription"][:100] + "..." if len(record["transcription"]) > 100 else record["transcription"]
            }
            for record in history
        ]
        return {"status": "success", "history": history_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load history: {str(e)}")


@app.get("/api/history/{session_id}")
async def get_history_detail(session_id: str):
    """获取特定会话的完整历史记录"""
    try:
        history = load_history()
        for record in history:
            if record["session_id"] == session_id:
                # 尝试从内存中恢复会话
                if session_id not in sessions:
                    try:
                        get_or_create_session(session_id, record["transcription"])
                        # 恢复对话历史到内存
                        if "chat_history" in record and record["chat_history"]:
                            chat_history = []
                            for msg_dict in record["chat_history"]:
                                if msg_dict["type"] == "HumanMessage":
                                    chat_history.append(HumanMessage(content=msg_dict["content"]))
                                elif msg_dict["type"] == "AIMessage":
                                    chat_history.append(AIMessage(content=msg_dict["content"]))
                            sessions[session_id]["chat_history"] = chat_history
                        print(f"Session restored from history: {session_id}")
                    except Exception as e:
                        print(f"Failed to restore session: {e}")
                
                return {
                    "status": "success",
                    "session_id": session_id,
                    "filename": record["filename"],
                    "upload_time": record["upload_time"],
                    "transcription": record["transcription"],
                    "summary": record["summary"],
                    "chat_history": record.get("chat_history", []),
                    "session_active": session_id in sessions
                }
        
        raise HTTPException(status_code=404, detail="History record not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load history detail: {str(e)}")


@app.delete("/api/history/{session_id}")
async def delete_history(session_id: str):
    """删除历史记录"""
    try:
        if delete_history_record(session_id):
            # 同时从内存中删除会话
            if session_id in sessions:
                del sessions[session_id]
            return {"status": "success", "message": "History record deleted"}
        else:
            raise HTTPException(status_code=404, detail="History record not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete history: {str(e)}")


@app.get("/debug/sessions")
async def debug_sessions():
    """调试端点：查看所有活动会话"""
    return {
        "active_sessions": len(sessions),
        "session_ids": list(sessions.keys()),
        "sessions_detail": {
            sid: {
                "transcription_length": len(sdata["transcription"]),
                "chat_history_count": len(sdata["chat_history"]),
                "last_access": sdata["last_access"].isoformat()
            }
            for sid, sdata in sessions.items()
        }
    }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取会话信息"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    return {
        "session_id": session_id,
        "transcription": session_data["transcription"],
        "chat_history_count": len(session_data["chat_history"]),
        "exists": True
    }


@app.post("/chat")
async def chat_with_context(request: ChatRequest):
    """
    基于转录文本的对话接口（流式响应）
    
    Args:
        request: ChatRequest对象，包含session_id和message
    
    Returns:
        SSE流式响应
    """
    # 调试信息
    print(f"Chat request received - Session ID: {request.session_id}")
    print(f"Current active sessions: {list(sessions.keys())}")
    
    # 检查会话是否存在
    if request.session_id not in sessions:
        error_detail = f"Session not found: {request.session_id}. Active sessions: {len(sessions)}"
        print(error_detail)
        raise HTTPException(status_code=404, detail="Session does not exist or has expired. Please upload audio again.")
    
    try:
        session_data = get_or_create_session(request.session_id)
        
        async def generate_chat_response():
            try:
                # 创建LLM
                llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.7,
                    openai_api_key=API_KEY
                )
                
                # 发送处理中状态
                yield f"data: {json.dumps({'type': 'status', 'message': 'Thinking...'}, ensure_ascii=False)}\n\n"
                
                # 从向量存储中检索相关文档
                docs = await asyncio.to_thread(
                    session_data["vectorstore"].similarity_search,
                    request.message,
                    k=3
                )
                
                # 构建上下文
                context = "\n\n".join([doc.page_content for doc in docs])
                
                # 构建对话历史
                history_text = ""
                for msg in session_data["chat_history"][-6:]:  # 只保留最近3轮对话
                    if isinstance(msg, HumanMessage):
                        history_text += f"User: {msg.content}\n"
                    elif isinstance(msg, AIMessage):
                        history_text += f"Assistant: {msg.content}\n"
                
                # 构建提示词
                system_prompt = f"""You are a helpful assistant. Answer the user's question based on the following context from an audio transcription.

Context:
{context}

Previous conversation:
{history_text}

Please provide a helpful and accurate answer based on the context. If the answer cannot be found in the context, say so."""
                
                # 调用LLM
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message}
                ]
                
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7
                )
                
                answer = response.choices[0].message.content
                
                # 保存对话历史到内存
                session_data["chat_history"].append(HumanMessage(content=request.message))
                session_data["chat_history"].append(AIMessage(content=answer))
                
                # 更新对话历史到持久化存储
                update_chat_history(request.session_id, session_data["chat_history"])
                
                # 流式发送答案（模拟流式效果）
                words = answer.split()
                for i, word in enumerate(words):
                    if i == 0:
                        content = word
                    else:
                        content = " " + word
                    yield f"data: {json.dumps({'type': 'chat_chunk', 'content': content}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.02)
                
                # 发送完成状态
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                
            except Exception as e:
                error_msg = f"Chat failed: {str(e)}"
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
        
        return StreamingResponse(
            generate_chat_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
