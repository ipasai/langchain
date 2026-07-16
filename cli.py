#!/usr/bin/env python3
"""
LangChain CLI 交互式應用
提供命令行介面讓使用者選擇模型、調整參數並輸入提示詞
"""

from llm_factory import LLMFactory, ModelProvider
from langchain_core.messages import HumanMessage
import sys

def print_header():
    """列印應用標題"""
    print("\n" + "=" * 60)
    print("🤖 LangChain 多模型交互式應用 (CLI 版本)")
    print("=" * 60 + "\n")

def select_provider():
    """讓使用者選擇模型提供者"""
    print("📋 請選擇 AI 模型提供者:")
    print("  1. Ollama (本地)")
    print("  2. OpenAI (雲端)")
    print("  3. Google Gemini (雲端)")
    
    choice = input("\n請輸入選擇 (1-3): ").strip()
    
    provider_map = {
        "1": ModelProvider.OLLAMA,
        "2": ModelProvider.OPENAI,
        "3": ModelProvider.GOOGLE,
    }
    
    if choice not in provider_map:
        print("❌ 無效的選擇，使用預設 Ollama 模型")
        return ModelProvider.OLLAMA
    
    return provider_map[choice]

def select_model(provider):
    """讓使用者選擇具體模型"""
    models = LLMFactory.get_available_models(provider)
    if not models:
        return None
    print(f"\n📋 請選擇 {provider.value.upper()} 模型:")
    for idx, model in enumerate(models, 1):
        formatted = LLMFactory.get_formatted_model_name(model)
        print(f"  {idx}. {formatted}")
    
    choice = input(f"\n請輸入選擇 (1-{len(models)}, 預設 1): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx]
    except ValueError:
        pass
    return models[0]

def get_prompt():
    """獲取使用者的提示詞"""
    print("\n📝 請輸入您的提示詞 (輸入 'quit' 結束):")
    print("-" * 60)
    
    try:
        prompt = input(">>> ").strip()
        return prompt if prompt else None
    except EOFError:
        return "quit"

def invoke_llm(provider, model_name, prompt):
    """呼叫 LLM 獲取回應"""
    try:
        print("\n⏳ 正在獲取回應...")
        llm = LLMFactory.get_llm(provider, model_name=model_name)
        messages = [HumanMessage(content=prompt)]
        
        print("\n✅ 回應內容:")
        print("-" * 60)
        # 實作串流輸出 (Streaming)
        for chunk in llm.stream(messages):
            print(chunk.content, end="", flush=True)
        print("\n" + "-" * 60)
        return True
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        print("💡 提示: 請檢查模型提供者的連線設定和 API 金鑰")
        return False

def main():
    """主程序"""
    print_header()
    
    # 選擇提供者
    provider = select_provider()
    print(f"\n✓ 已選擇提供者: {provider.value.upper()}")
    
    # 選擇模型
    model_name = select_model(provider)
    print(f"✓ 已選擇模型: {model_name}")
    
    # 交互式循環
    print("\n" + "=" * 60)
    print("🎯 已準備好接受您的提示詞!")
    print("=" * 60)
    
    while True:
        prompt = get_prompt()
        
        if not prompt:
            print("⚠️  提示詞不能為空，請重試")
            continue
        
        if prompt.lower() == "quit":
            print("\n👋 感謝使用 LangChain CLI 應用!")
            break
        
        invoke_llm(provider, model_name, prompt)
        
        # 詢問是否繼續
        again = input("\n繼續提問? (是/否): ").strip().lower()
        if again not in ["是", "y", "yes", ""]:
            print("\n👋 感謝使用 LangChain CLI 應用!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  應用已中斷")
        sys.exit(0)
