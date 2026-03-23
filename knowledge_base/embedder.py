from typing import List
from zhipuai import ZhipuAI

class DenseEmbedder:
    """
    负责生成稠密向量（Dense Vector，ZhipuAI embedding-3，默认 2048 维）。
    """
    def __init__(self, api_key: str, model_name: str = "embedding-3"):
        self.client = ZhipuAI(api_key=api_key)
        self.model_name = model_name
        self.dim = 2048

    def embed_text(self, text: str) -> List[float]:
        """
        对单条文本生成稠密向量
        """
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成稠密向量 (智谱 API 支持批量 input)
        """
        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts
        )
        return [item.embedding for item in response.data]
