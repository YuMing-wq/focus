#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 处理Windows编码问题
"""
import sys
import os

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 检查.env文件
if not os.path.exists('.env'):
    print("WARNING: .env file not found!")
    print("Please create .env file with:")
    print("OPENAI_API_KEY=your_api_key_here")
    print()

# 启动应用
if __name__ == "__main__":
    import uvicorn
    
    print("Starting server at http://localhost:8000")
    print("Press CTRL+C to stop")
    print()
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

