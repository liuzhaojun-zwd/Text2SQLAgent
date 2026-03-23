import json
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from pymilvus import Collection, connections

class HybridRetriever:
    """
    负责执行 Milvus 的混合检索 (Dense + Sparse) 并执行 RRF 融合
    """
    def __init__(self, host: str, port: int, collection_name: str, embedder, indexer, graph_path: str = None, rewriter=None):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedder = embedder
        self.indexer = indexer
        self.rewriter = rewriter
        self.collection = None
        self.graph = []
        
        # 加载外键图谱
        if graph_path:
            try:
                with open(graph_path, "r", encoding="utf-8") as f:
                    self.graph = json.load(f)
            except Exception as e:
                print(f"Failed to load topology graph from {graph_path}: {e}")
        
        # 连接 Milvus
        try:
            connections.connect("default", host=self.host, port=self.port)
            self.collection = Collection(self.collection_name)
            self.collection.load()
        except Exception as e:
            print(f"Failed to connect to Milvus or load collection: {e}")
            
    def _search_dense(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """执行稠密向量检索"""
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

    def _search_sparse(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """执行稀疏向量(BM25)检索"""
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
        
    def _rrf(self, dense_hits: List[Dict[str, Any]], sparse_hits: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        """执行 RRF (Reciprocal Rank Fusion) 融合"""
        # 合并结果并按 ID 分组
        fused_scores = defaultdict(float)
        items_map = {}
        
        # 处理稠密结果
        for hit in dense_hits:
            item_id = hit["id"]
            fused_scores[item_id] += 1.0 / (k + hit["rank"])
            if item_id not in items_map:
                items_map[item_id] = hit
                
        # 处理稀疏结果
        for hit in sparse_hits:
            item_id = hit["id"]
            fused_scores[item_id] += 1.0 / (k + hit["rank"])
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
            
        return final_results

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """主检索接口：并发执行稠密和稀疏检索，然后 RRF 融合，最后基于外键图谱进行扩展，返回 Top K"""
        # 0. Query 改写（如果配置了 Rewriter）
        if self.rewriter:
            enhanced_query = self.rewriter.rewrite(query)
            print(f"🔄 原始 Query: {query}")
            print(f"✨ 改写后 Query: {enhanced_query}")
        else:
            enhanced_query = query
            
        # 1. 执行向量检索与 RRF 融合
        dense_hits = self._search_dense(enhanced_query, limit=top_k * 2)
        sparse_hits = self._search_sparse(enhanced_query, limit=top_k * 2)
        
        fused_results = self._rrf(dense_hits, sparse_hits)
        
        # 提取当前召回的表集合
        retrieved_tables = {hit["table_name"] for hit in fused_results}
        
        # 2. 基于外键图谱进行上下文扩展 (Graph Expansion)
        # 如果 A 表被召回，且 A 表和 B 表有外键关联，我们把 B 表也加入考虑范围内
        expanded_tables = set()
        
        # 解析 topology_graph.json 的结构： "source_table.source_column": "target_table.target_column"
        if isinstance(self.graph, dict):
            for source, target in self.graph.items():
                source_table = source.split('.')[0]
                target_table = target.split('.')[0]
                
                if source_table in retrieved_tables and target_table not in retrieved_tables:
                    expanded_tables.add(target_table)
                elif target_table in retrieved_tables and source_table not in retrieved_tables:
                    expanded_tables.add(source_table)
        elif isinstance(self.graph, list):
            # 兼容可能的列表结构 (取决于 graph_builder 的具体实现)
            for edge in self.graph:
                if isinstance(edge, dict):
                    source_table = edge.get("source_table")
                    target_table = edge.get("target_table")
                    
                    if source_table and target_table:
                        if source_table in retrieved_tables and target_table not in retrieved_tables:
                            expanded_tables.add(target_table)
                        elif target_table in retrieved_tables and source_table not in retrieved_tables:
                            expanded_tables.add(source_table)
                
        # 3. 如果有扩展的表，我们需要把这些表的 schema 也补充进来
        # 注意：这里为了简化，我们直接从已有的数据或者通过重新查一次 Milvus 来获取扩展表的元信息
        # 生产环境中，最好有一个本地的 Table Schema 缓存字典直接提取
        if expanded_tables and self.collection:
            # 使用 expr 进行标量过滤，把扩展表的字段全部拉出来（这里限制每个表取几个关键字段防止撑爆）
            # Milvus expr 语法: table_name in ["table1", "table2"]
            tables_str = ", ".join([f"'{t}'" for t in expanded_tables])
            expr = f"table_name in [{tables_str}]"
            
            try:
                # 注意：query 方法在部分版本中可能不返回 distance/score，需要手动赋值
                expanded_results = self.collection.query(
                    expr=expr,
                    output_fields=["table_name", "column_name", "text"],
                    limit=len(expanded_tables) * 10 # 放宽限制，让扩展表的字段更多地进入
                )
                
                # 为扩展进来的结果赋予一个基础分数，追加到 fused_results 后面
                for i, hit in enumerate(expanded_results):
                    # 防止把已经存在的结果重复加进来
                    if hit.get("id") not in {r["id"] for r in fused_results}:
                        # 降低扩展字段的兜底分数，避免过度挤占原始匹配项的位置
                        base_score = 0.005 - (i * 0.00001) 
                        fused_results.append({
                            "id": hit.get("id", f"exp_{i}"),
                            "table_name": hit.get("table_name"),
                            "column_name": hit.get("column_name"),
                            "text": hit.get("text"),
                            "rrf_score": max(0.0001, base_score), 
                            "rrf_rank": 200 + i,
                            "is_expanded": True # 标记这是通过图谱扩展来的
                        })
            except Exception as e:
                print(f"Graph expansion query failed: {e}")
                
        # 由于加入扩展表可能会把无关字段排到前面，我们需要重新按照 rrf_score 排序
        fused_results = sorted(fused_results, key=lambda x: x.get("rrf_score", 0), reverse=True)
                
        # 返回前 Top K 个结果
        return fused_results[:top_k]
