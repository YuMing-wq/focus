#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的前端连接问题
"""

import requests
import time

def test_api_endpoints():
    """测试API端点"""
    base_url = "http://localhost:8000"

    print("测试API端点...")

    # 测试GET /
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("[OK] GET / - 正常")
        else:
            print(f"[ERROR] GET / - 状态码: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] GET / - 连接失败: {e}")
        return False

    # 测试GET /process-with-summary (应该返回405)
    try:
        response = requests.get(f"{base_url}/process-with-summary")
        if response.status_code == 405:
            print("[OK] GET /process-with-summary - 正确返回405 Method Not Allowed")
        else:
            print(f"[WARN] GET /process-with-summary - 意外状态码: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] GET /process-with-summary - 连接失败: {e}")

    # 测试POST /process-with-summary (需要文件，但应该返回400)
    try:
        response = requests.post(f"{base_url}/process-with-summary")
        if response.status_code == 422:  # FastAPI的表单数据验证错误
            print("[OK] POST /process-with-summary - 正确处理POST请求")
        else:
            print(f"[WARN] POST /process-with-summary - 状态码: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] POST /process-with-summary - 连接失败: {e}")

    return True

def main():
    """主函数"""
    print("=" * 50)
    print("音频转录和总结工具 - 修复测试")
    print("=" * 50)

    # 等待一下确保服务器启动
    print("等待服务器启动...")
    time.sleep(2)

    if test_api_endpoints():
        print("\n[OK] API测试完成")
        print("\n现在可以测试前端:")
        print("1. 打开浏览器访问 http://localhost:8080")
        print("2. 上传音频文件")
        print("3. 检查是否还有405错误")
    else:
        print("\n[ERROR] API测试失败，请检查服务器是否正常启动")

if __name__ == "__main__":
    main()
