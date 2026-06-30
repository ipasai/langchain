import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import Optional, Dict, Any
from enum import Enum

# 讀取 .env 檔案
load_dotenv()

class ModelProvider(Enum):
    """支援的模型提供者"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    GOOGLE = "google"

class LLMFactory:
    """專門用來產生不同 AI 模型連線物件的工廠類別"""

    # 定義每個提供者的可用模型
    AVAILABLE_MODELS = {
        ModelProvider.OLLAMA: ["llama3", "mistral", "neural-chat", "dolphin-mixtral"],
        ModelProvider.OPENAI: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        ModelProvider.GOOGLE: ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    }

    @staticmethod
    def get_available_models(provider: ModelProvider) -> list:
        """取得指定提供者的可用模型清單"""
        return LLMFactory.AVAILABLE_MODELS.get(provider, [])

    @staticmethod
    def resolve_temperature(temperature: Optional[float] = None) -> float:
        """解析溫度，優先使用傳入值，否則從 .env 讀取"""
        if temperature is not None:
            return temperature

        env_temperature = os.getenv("TEMPERATURE")
        if env_temperature is not None:
            try:
                return float(env_temperature)
            except ValueError:
                pass

        return 0.7

    @staticmethod
    def get_ollama_llm(
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ChatOllama:
        """
        產生專門用來使用 Ollama 連線的物件 (本地)
        
        Args:
            model_name: 模型名稱，預設從 .env 讀取
            temperature: 溫度參數 (0.0-1.0)
            **kwargs: 其他參數
        """
        selected_model = model_name or os.getenv("OLLAMA_MODEL", "llama3")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        resolved_temperature = LLMFactory.resolve_temperature(temperature)
        
        print(f"[系統] 正在初始化本地 Ollama 物件 (模型: {selected_model})...")
        
        return ChatOllama(
            base_url=base_url,
            model=selected_model,
            temperature=resolved_temperature,
            **kwargs
        )

    @staticmethod
    def get_openai_llm(
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ChatOpenAI:
        """
        產生專門用來操作 OpenAI 的物件 (雲端)
        
        Args:
            model_name: 模型名稱，預設從 .env 讀取
            temperature: 溫度參數 (0.0-1.0)
            **kwargs: 其他參數
        """
        selected_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        resolved_temperature = LLMFactory.resolve_temperature(temperature)
        
        if not api_key or api_key == "your_openai_api_key_here":
            raise ValueError("錯誤: 請在 .env 檔案中設定正確的 OPENAI_API_KEY")
            
        print(f"[系統] 正在初始化 OpenAI 物件 (模型: {selected_model})...")
        
        return ChatOpenAI(
            api_key=api_key,
            model=selected_model,
            temperature=resolved_temperature,
            **kwargs
        )

    @staticmethod
    def get_google_llm(
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ChatGoogleGenerativeAI:
        """
        產生專門用來操作 Google Gemini 的物件 (雲端)
        
        Args:
            model_name: 模型名稱，預設從 .env 讀取
            temperature: 溫度參數 (0.0-1.0)
            **kwargs: 其他參數
        """
        selected_model = model_name or os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        api_key = os.getenv("GOOGLE_API_KEY")
        resolved_temperature = LLMFactory.resolve_temperature(temperature)
        
        if not api_key or api_key == "your_google_ai_studio_api_key_here":
            raise ValueError("錯誤: 請在 .env 檔案中設定正確的 GOOGLE_API_KEY")
            
        print(f"[系統] 正在初始化 Google Gemini 物件 (模型: {selected_model})...")
        
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=selected_model,
            temperature=resolved_temperature,
            **kwargs
        )

    @staticmethod
    def get_llm(
        provider: ModelProvider,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        根據提供者類型動態取得 LLM 物件
        
        Args:
            provider: 模型提供者
            model_name: 模型名稱
            temperature: 溫度參數
            **kwargs: 其他參數
        """
        if provider == ModelProvider.OLLAMA:
            return LLMFactory.get_ollama_llm(model_name, temperature, **kwargs)
        elif provider == ModelProvider.OPENAI:
            return LLMFactory.get_openai_llm(model_name, temperature, **kwargs)
        elif provider == ModelProvider.GOOGLE:
            return LLMFactory.get_google_llm(model_name, temperature, **kwargs)
        else:
            raise ValueError(f"未知的提供者: {provider}")