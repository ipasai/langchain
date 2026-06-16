from llm_factory import LLMFactory
from langchain_core.messages import HumanMessage

def test_llm_connections():
    # 測試用的問題
    test_prompt = "請用一句話解釋什麼是 LangChain。"
    messages = [HumanMessage(content=test_prompt)]

    print("=== 開始測試 LangChain 模型連線 ===\n")

    # # 1. 測試 Ollama 物件
    # try:
    #     ollama_llm = LLMFactory.get_ollama_llm()
    #     ollama_response = ollama_llm.invoke(messages)
    #     print(f"【Ollama 回應】:\n{ollama_response.content}\n")
    # except Exception as e:
    #     print(f"❌ Ollama 測試失敗，請檢查 Ollama 是否已在後台啟動。錯誤訊息: {e}\n")

    # print("-" * 50)

    # # 2. 測試 OpenAI 物件
    # try:
    #     openai_llm = LLMFactory.get_openai_llm()
    #     openai_response = openai_llm.invoke(messages)
    #     print(f"【OpenAI 回應】:\n{openai_response.content}\n")
    # except Exception as e:
    #     print(f"❌ OpenAI 測試失敗，請檢查 .env 的 API Key。錯誤訊息: {e}\n")

    # 3. 測試 Google Gemini 物件
    try:
        google_llm = LLMFactory.get_google_llm()
        google_response = google_llm.invoke(messages)
        print(f"【Google Gemini 回應】:\n{google_response.content}\n")
    except Exception as e:
        print(f"❌ Google Gemini 測試失敗，請檢查 .env 的 GOOGLE_API_KEY。錯誤訊息: {e}\n")

    print("-" * 50)

if __name__ == "__main__":
    test_llm_connections()