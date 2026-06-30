#!/usr/bin/env python3
"""
LangChain 主入口點
提供選擇使用 CLI 或 Web UI 應用的主菜單
"""

import sys
import subprocess

def print_menu():
    """列印主菜單"""
    print("\n" + "=" * 60)
    print("🤖 LangChain 多模型應用 - 主菜單")
    print("=" * 60)
    print("\n請選擇運行模式:\n")
    print("  1️⃣  CLI 模式 (命令行交互)")
    print("  2️⃣  Web UI 模式 (Streamlit 網頁)")
    print("  3️⃣  測試連線 (測試所有模型連線)")
    print("  0️⃣  退出\n")

def run_cli():
    """運行 CLI 應用"""
    print("\n啟動 CLI 應用...\n")
    try:
        import cli
        cli.main()
    except Exception as e:
        print(f"❌ CLI 應用出錯: {e}")

def run_streamlit():
    """運行 Streamlit 應用"""
    print("\n啟動 Streamlit Web UI...\n")
    
    # 檢查 streamlit 是否已安裝
    try:
        import streamlit
        print("💡 應用將在瀏覽器中打開。如果沒有自動打開，請訪問: http://localhost:8501\n")
        try:
            import subprocess
            subprocess.run(["streamlit", "run", "app.py"], cwd=".")
        except FileNotFoundError:
            print("❌ 未找到 streamlit 命令。請運行: pip install streamlit")
    except ImportError:
        print("⚠️  Streamlit 未安裝")
        print("\n若要使用 Web UI，請安裝 Streamlit:")
        print("  pip install streamlit")
        print("\n或者使用 CLI 版本:")
        print("  python cli.py")
        input("\n按 Enter 返回菜單...")
        return

def test_connections():
    """測試所有模型連線"""
    from llm_factory import LLMFactory, ModelProvider
    from langchain_core.messages import HumanMessage
    
    test_prompt = "請用一句話解釋什麼是 LangChain。"
    messages = [HumanMessage(content=test_prompt)]
    
    print("\n" + "=" * 60)
    print("🧪 開始測試 LangChain 模型連線")
    print("=" * 60 + "\n")
    
    providers = [
        (ModelProvider.OLLAMA, "Ollama (本地)"),
        (ModelProvider.OPENAI, "OpenAI (雲端)"),
        (ModelProvider.GOOGLE, "Google Gemini (雲端)"),
    ]
    
    for provider, label in providers:
        print(f"\n📋 測試 {label}...")
        print("-" * 60)
        
        try:
            llm = LLMFactory.get_llm(provider)
            response = llm.invoke(messages)
            print(f"✅ 連線成功!")
            print(f"回應: {response.content[:100]}...")
        except Exception as e:
            print(f"❌ 連線失敗: {e}")
    
    print("\n" + "=" * 60)
    print("🧪 測試完成")
    print("=" * 60 + "\n")

def main():
    """主程序"""
    while True:
        print_menu()
        choice = input("請輸入選擇 (0-3): ").strip()
        
        if choice == "1":
            run_cli()
            break
        elif choice == "2":
            run_streamlit()
            break
        elif choice == "3":
            test_connections()
        elif choice == "0":
            print("\n👋 謝謝使用!\n")
            sys.exit(0)
        else:
            print("\n❌ 無效的選擇，請重試\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  應用已中斷")
        sys.exit(0)