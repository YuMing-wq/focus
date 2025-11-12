#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频转录和总结Web服务
使用FastAPI构建，支持文件上传和流式响应
"""

import os
import asyncio
import json
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI


# 加载环境变量
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("未找到 OPENAI_API_KEY 环境变量，请创建 .env 文件")

# 初始化OpenAI客户端
client = OpenAI(api_key=API_KEY)


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
        "version": "2.0.0",
        "description": "使用OpenAI Whisper和GPT-4o-mini进行音频转录和智能总结",
        "endpoints": {
            "GET /": "API信息",
            "POST /process": "音频转录（不含总结）",
            "POST /process-with-summary": "音频转录和流式总结"
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

                # 流式发送总结
                async for summary_event in summarize_text_stream(transcribed_text):
                    yield summary_event

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
