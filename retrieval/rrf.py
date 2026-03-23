from typing import List, Dict, Any
from collections import defaultdict

class RRFFusion:
    """
    独立封装的 RRF (Reciprocal Rank Fusion) 多路召回融合算法模块
    """
    def __init__(self, k: int = 60):
        """
        :param k: RRF 算法的平滑常数，默认 60
        """
        self.k = k

    def fuse(self, dense_hits: List[Dict[str, Any]], sparse_hits: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        执行 RRF 融合
        :param dense_hits: 稠密向量检索结果列表 (需要包含 id 和 rank)
        :param sparse_hits: 稀疏向量检索结果列表 (需要包含 id 和 rank)
        :param top_k: 最终返回的截断数量，默认 10
        :return: 融合并重新排序后的字典列表
        """
        # 合并结果并按 ID 分组
        fused_scores = defaultdict(float)
        items_map = {}
        
        # 处理稠密结果
        for hit in dense_hits:
            item_id = hit["id"]
            fused_scores[item_id] += 1.0 / (self.k + hit.get("rank", 999))
            if item_id not in items_map:
                items_map[item_id] = hit
                
        # 处理稀疏结果
        for hit in sparse_hits:
            item_id = hit["id"]
            fused_scores[item_id] += 1.0 / (self.k + hit.get("rank", 999))
            if item_id not in items_map:
                items_map[item_id] = hit
                
        # 按照 RRF 分数排序
        sorted_items = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 组装最终结果
        final_results = []
        for rank, (item_id, score) in enumerate(sorted_items):
            item = items_map[item_id].copy()
            item["rrf_score"] = score
            item["rrf_rank"] = rank + 1
            final_results.append(item)
            
        return final_results[:top_k]
