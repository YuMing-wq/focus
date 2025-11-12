#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频转录和总结工具启动脚本
同时启动后端API服务和前端HTTP服务器
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path


def check_requirements():
    """检查环境和依赖"""
    print("正在检查环境...")

    # 检查Python版本
    if sys.version_info < (3, 8):
        print("错误: 需要Python 3.8或更高版本")
        sys.exit(1)

    # 检查.env文件
    if not Path('.env').exists():
        print("警告: 未找到.env文件")
        print("请复制.env.example为.env，并填入你的OpenAI API密钥")
        print("从 https://platform.openai.com/api-keys 获取API密钥")
        return False

    # 检查API密钥
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        print("警告: 请在.env文件中设置有效的OPENAI_API_KEY")
        return False

    print("✓ 环境检查通过")
    return True


def start_backend():
    """启动后端服务"""
    print("启动后端服务 (http://localhost:8000)...")
    try:
        subprocess.run([
            sys.executable, "app.py"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"后端服务启动失败: {e}")
        return False
    except KeyboardInterrupt:
        print("后端服务已停止")
        return True
    return True


def start_frontend():
    """启动前端HTTP服务器"""
    print("启动前端服务器 (http://localhost:8080)...")
    try:
        subprocess.run([
            sys.executable, "-m", "http.server", "8080"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"前端服务器启动失败: {e}")
        return False
    except KeyboardInterrupt:
        print("前端服务器已停止")
        return True
    return True


def main():
    """主函数"""
    print("=" * 50)
    print("音频转录和总结工具")
    print("=" * 50)

    # 检查环境
    if not check_requirements():
        print("\n请解决上述问题后重新运行")
        sys.exit(1)

    print("\n正在启动服务...")
    print("后端API: http://localhost:8000")
    print("前端界面: http://localhost:8080")
    print("按 Ctrl+C 停止服务")
    print("-" * 50)

    try:
        # 尝试同时启动两个服务
        # 注意：在Windows上，这可能需要管理员权限或额外的配置

        # 启动后端服务（在后台）
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()

        # 等待一下让后端启动
        time.sleep(2)

        # 启动前端服务
        start_frontend()

    except KeyboardInterrupt:
        print("\n正在停止服务...")
        sys.exit(0)
    except Exception as e:
        print(f"启动失败: {e}")
        print("\n你也可以手动启动服务:")
        print("1. 终端1: python app.py")
        print("2. 终端2: python -m http.server 8080")
        sys.exit(1)


if __name__ == "__main__":
    main()
