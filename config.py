import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API & App Settings
    APP_NAME: str = "Text-to-SQL API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Milvus Configuration
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: str = os.getenv("MILVUS_PORT", "19530")
    MILVUS_USER: str = os.getenv("MILVUS_USER", "root")
    MILVUS_PASSWORD: str = os.getenv("MILVUS_PASSWORD", "123456")
    MILVUS_DB_NAME: str = os.getenv("MILVUS_DB_NAME", "text2sql")
    MILVUS_COLLECTION_NAME: str = "schema_knowledge_base"

    # MySQL Database Configuration
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: str = os.getenv("MYSQL_PORT", "3306")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "123456")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "text2sql")

    # Read-only MySQL Configuration for Execution Sandbox
    MYSQL_RO_USER: str = os.getenv("MYSQL_RO_USER", "readonly_user")
    MYSQL_RO_PASSWORD: str = os.getenv("MYSQL_RO_PASSWORD", "readonly_pass")

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))

    # LLM & Embedding Model Configuration
    # Using ZhipuAI models as per rules
    ZHIPUAI_API_KEY: str = os.getenv("ZHIPUAI_API_KEY", "a917c5652c2d4c89a3ac35e0a2213fcc.eSdV17PsW9YqxRj3")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "glm-4.7")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "embedding-3")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# SQLAlchemy Database URLs
DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"
READONLY_DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_RO_USER}:{settings.MYSQL_RO_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"
