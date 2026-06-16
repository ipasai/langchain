import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

# 讀取 .env 檔案
load_dotenv()

class LLMFactory:
    """專門用來產生不同 AI 模型連線物件的工廠類別"""

    @staticmethod
    def get_ollama_llm(model_name: str = None, temperature: float = 0.7) -> ChatOllama:
        """
        功能 4: 產生專門用來使用 Ollama 連線的物件 (本地)
        """
        # 如果沒指定模型，就從 .env 讀取預設值
        selected_model = model_name or os.getenv("OLLAMA_MODEL", "llama3")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        print(f"[系統] 正在初始化本地 Ollama 物件 (模型: {selected_model})...")
        
        return ChatOllama(
            base_url=base_url,
            model=selected_model,
            temperature=temperature
        )

    @staticmethod
    def get_openai_llm(model_name: str = None, temperature: float = 0.7) -> ChatOpenAI:
        """
        功能 5: 產生專門用來操作 OpenAI 的物件 (雲端)
        """
        # 如果沒指定模型，就從 .env 讀取預設值
        selected_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError("錯誤: 請在 .env 檔案中設定正確的 OPENAI_API_KEY")
            
        print(f"[系統] 正在初始化 OpenAI 物件 (模型: {selected_model})...")
        
        return ChatOpenAI(
            api_key=api_key,
            model=selected_model,
            temperature=temperature
        )
    
    """專門用來產生不同 AI 模型連線物件的工廠類別"""

    # ... 保留原本的 get_ollama_llm 與 get_openai_llm ...

    @staticmethod
    def get_google_llm(model_name: str = None, temperature: float = 0.7) -> ChatGoogleGenerativeAI:
        """
        功能: 產生專門用來操作 Google Gemini 的物件 (雲端)
        """
        # 如果沒指定模型，就從 .env 讀取預設值
        selected_model = model_name or os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key or api_key == "your_google_ai_studio_api_key_here":
            raise ValueError("錯誤: 請在 .env 檔案中設定正確的 GOOGLE_API_KEY")
            
        print(f"[系統] 正在初始化 Google Gemini 物件 (模型: {selected_model})...")
        
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=selected_model,
            temperature=temperature
        )