#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频转录和总结工具
使用OpenAI Whisper API进行音频转录，使用GPT-4o-mini进行文本总结
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI


def load_environment():
    """加载环境变量"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: 未找到 OPENAI_API_KEY 环境变量")
        print("请创建 .env 文件并设置 OPENAI_API_KEY")
        sys.exit(1)
    return api_key


def transcribe_audio(client: OpenAI, audio_file_path: str) -> str:
    """
    使用Whisper API转录音频文件
    
    Args:
        client: OpenAI客户端实例
        audio_file_path: 音频文件路径
        
    Returns:
        转录的文本内容
    """
    print(f"正在转录音频文件: {audio_file_path}")
    
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        print("✓ 音频转录完成")
        return transcript
    except Exception as e:
        print(f"错误: 转录失败 - {str(e)}")
        sys.exit(1)


def summarize_text(client: OpenAI, text: str) -> str:
    """
    使用GPT-4o-mini模型总结文本（流式输出）
    
    Args:
        client: OpenAI客户端实例
        text: 需要总结的文本
        
    Returns:
        总结后的文本
    """
    print("正在生成文本总结...")
    print("-"*50)
    
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
        
        summary_chunks = []
        print("总结内容: ", end="", flush=True)
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                summary_chunks.append(content)
        
        print("\n" + "-"*50)
        print("✓ 文本总结完成")
        
        summary = "".join(summary_chunks)
        return summary
    except Exception as e:
        print(f"\n错误: 总结失败 - {str(e)}")
        sys.exit(1)


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python main.py <音频文件路径>")
        print("示例: python main.py audio.mp3")
        sys.exit(1)
    
    audio_file_path = sys.argv[1]
    
    # 检查文件是否存在
    if not os.path.exists(audio_file_path):
        print(f"错误: 文件不存在 - {audio_file_path}")
        sys.exit(1)
    
    # 加载环境变量
    api_key = load_environment()
    
    # 初始化OpenAI客户端
    client = OpenAI(api_key=api_key)
    
    # 步骤1: 转录音频
    print("\n" + "="*50)
    print("步骤 1/2: 音频转录")
    print("="*50)
    transcribed_text = transcribe_audio(client, audio_file_path)
    
    # 显示转录结果
    print("\n转录结果:")
    print("-"*50)
    print(transcribed_text)
    print("-"*50)
    
    # 步骤2: 总结文本
    print("\n" + "="*50)
    print("步骤 2/2: 文本总结")
    print("="*50)
    summary = summarize_text(client, transcribed_text)
    
    # 显示总结结果
    print("\n总结结果:")
    print("-"*50)
    print(summary)
    print("-"*50)
    
    # 保存结果到文件
    output_file = Path(audio_file_path).stem + "_result.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write("音频转录和总结结果\n")
        f.write("="*50 + "\n\n")
        f.write("原始音频文件: " + audio_file_path + "\n\n")
        f.write("转录文本:\n")
        f.write("-"*50 + "\n")
        f.write(transcribed_text + "\n")
        f.write("-"*50 + "\n\n")
        f.write("总结:\n")
        f.write("-"*50 + "\n")
        f.write(summary + "\n")
        f.write("-"*50 + "\n")
    
    print(f"\n✓ 结果已保存到: {output_file}")


if __name__ == "__main__":
    main()

