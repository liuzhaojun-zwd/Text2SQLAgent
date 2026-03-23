from typing import List, Dict, Any
from pymilvus import Collection

class SparseRetriever:
    """
    独立封装的稀疏向量(BM25)检索模块 (Top-15)
    """
    def __init__(self, collection: Collection, indexer):
        """
        :param collection: 已经建立连接的 Milvus Collection 实例
        :param indexer: 提供 generate_sparse_vector 方法的 BM25 Indexer 实例
        """
        self.collection = collection
        self.indexer = indexer

    def search(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        执行稀疏向量检索
        :param query: 改写后的增强查询文本
        :param limit: 召回数量，默认 15
        :return: 包含 id, table_name, column_name, text, score, rank 的字典列表
        """
        if not self.collection:
            return []
            
        # 生成查询的稀疏向量
        query_sparse = self.indexer.generate_sparse_vector(query)
        
        search_params = {
            "metric_type": "IP",
            "params": {"drop_ratio_build": 0.2},
        }
        
        results = self.collection.search(
            data=[query_sparse],
            anns_field="sparse_vector",
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
