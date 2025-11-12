#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本 - 检查对话功能问题
"""
import requests
import json
import time
import os

API_BASE_URL = "http://localhost:8000"

def check_server():
    """检查服务器状态"""
    print("=" * 60)
    print("1. Checking server status...")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print("[OK] Server is running")
            print(f"  Version: {data.get('version')}")
            print(f"  Endpoints: {list(data.get('endpoints', {}).keys())}")
            return True
        else:
            print(f"[FAIL] Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Cannot connect to server: {e}")
        print("  Please start the server: python run_app.py")
        return False


def check_api_key():
    """检查API密钥配置"""
    print("\n" + "=" * 60)
    print("2. Checking OpenAI API key...")
    print("=" * 60)
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            content = f.read()
            if 'OPENAI_API_KEY' in content:
                print("[OK] .env file exists with OPENAI_API_KEY")
                if 'your_' in content or 'sk-' not in content:
                    print("  WARNING: API key might not be configured correctly")
                return True
            else:
                print("[FAIL] OPENAI_API_KEY not found in .env")
                return False
    else:
        print("[FAIL] .env file not found")
        print("  Create .env file with: OPENAI_API_KEY=your_key_here")
        return False


def check_debug_sessions():
    """检查活动会话"""
    print("\n" + "=" * 60)
    print("3. Checking active sessions...")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE_URL}/debug/sessions")
        if response.status_code == 200:
            data = response.json()
            session_count = data.get('active_sessions', 0)
            print("[OK] Debug endpoint accessible")
            print(f"  Active sessions: {session_count}")
            
            if session_count > 0:
                print(f"  Session IDs: {data.get('session_ids', [])}")
                for sid, details in data.get('sessions_detail', {}).items():
                    print(f"    - {sid[:8]}...")
                    print(f"      Transcription: {details['transcription_length']} chars")
                    print(f"      Chat history: {details['chat_history_count']} messages")
            else:
                print("  No active sessions (upload an audio file to create one)")
            return True
        else:
            print(f"[FAIL] Debug endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Error checking sessions: {e}")
        return False


def test_chat_without_session():
    """测试无效会话的错误处理"""
    print("\n" + "=" * 60)
    print("4. Testing error handling (invalid session)...")
    print("=" * 60)
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "session_id": "invalid-test-session-id",
                "message": "Test message"
            }
        )
        if response.status_code == 404:
            print("[OK] Error handling works correctly (404 for invalid session)")
            return True
        else:
            print(f"[FAIL] Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Error during test: {e}")
        return False


def main():
    """运行所有诊断检查"""
    print("\nChat Feature Diagnostic Tool\n")
    
    results = []
    
    # 检查1: 服务器状态
    if not check_server():
        print("\n❌ Server is not running. Please start it first.")
        return
    results.append(True)
    
    # 检查2: API密钥
    results.append(check_api_key())
    
    # 检查3: 会话状态
    results.append(check_debug_sessions())
    
    # 检查4: 错误处理
    results.append(test_chat_without_session())
    
    # 总结
    print("\n" + "=" * 60)
    print("DIAGNOSIS SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if all(results):
        print("\n[OK] All checks passed!")
        print("\nIf you still get 404 errors:")
        print("1. Open browser console (F12) and check for errors")
        print("2. Look at the Network tab to see the actual request/response")
        print("3. Check server console for session creation logs")
        print("4. Ensure audio file is processed completely before chatting")
    else:
        print("\n[WARNING] Some checks failed. Please fix the issues above.")
    
    print("\nFor more help, check:")
    print("- CHAT_FEATURE_GUIDE.md")
    print("- QUICK_START.md")


if __name__ == "__main__":
    main()

