import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr

load_dotenv()


def get_llm(llm_type: str = "openai"):
    """openai = Azure OpenAI; ollama = local Ollama (OLLAMA_MODEL, OLLAMA_BASE_URL)."""
    if llm_type == "openai":
        api_key_raw = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")
        version = os.getenv("AZURE_OPENAI_MODEL_VERSION", "2024-12-01-preview")
        return AzureChatOpenAI(
            api_key=SecretStr(api_key_raw) if api_key_raw else None,
            azure_endpoint=endpoint,
            api_version=version,
            model=model,
        )
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen3.5")
    return ChatOllama(model=ollama_model, base_url=base_url)


if __name__ == "__main__":
    llm = get_llm(llm_type="openai")
    print(llm.invoke("Hello, how are you?").content)
