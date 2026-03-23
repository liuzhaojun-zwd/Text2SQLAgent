from typing import List, Dict, Any
from pymilvus import Collection

class DenseRetriever:
    """
    独立封装的稠密向量检索模块 (Top-15)
    """
    def __init__(self, collection: Collection, embedder):
        """
        :param collection: 已经建立连接的 Milvus Collection 实例
        :param embedder: 提供 embed_batch 方法的向量化模型实例
        """
        self.collection = collection
        self.embedder = embedder

    def search(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        执行稠密向量检索
        :param query: 改写后的增强查询文本
        :param limit: 召回数量，默认 15
        :return: 包含 id, table_name, column_name, text, score, rank 的字典列表
        """
        if not self.collection:
            return []
            
        # 生成查询向量
        query_vector = self.embedder.embed_batch([query])[0]
        
        search_params = {
            "metric_type": "IP",
            "params": {"nprobe": 10},
        }
        
        results = self.collection.search(
            data=[query_vector],
            anns_field="dense_vector",
            param=search_params,
            limit=limit,
            expr=None,
            output_fields=["table_name", "column_name", "text"]
        )
        
        hits = []
        if results and len(results) > 0:
            for hit in results[0]:
                hits.append({
                    "id": hit.id,
                    "table_name": hit.entity.get("table_name"),
                    "column_name": hit.entity.get("column_name"),
                    "text": hit.entity.get("text"),
                    "score": hit.distance,
                    "rank": len(hits) + 1
                })
        return hits
