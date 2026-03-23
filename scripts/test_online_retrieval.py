import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymilvus import Collection, connections
from text_to_sql.config import settings
from text_to_sql.knowledge_base.embedder import DenseEmbedder
from text_to_sql.knowledge_base.bm25_indexer import BM25Indexer
from text_to_sql.knowledge_base.query_rewriter import QueryRewriter

from text_to_sql.retrieval.dense import DenseRetriever
from text_to_sql.retrieval.sparse import SparseRetriever
from text_to_sql.retrieval.rrf import RRFFusion
from text_to_sql.retrieval.topology import TopologyExpander

def main():
    print("🚀 初始化在线检索流程测试...")
    
    # 1. 初始化基础组件
    print("1️⃣ 初始化 Embedder, Indexer 和 Rewriter...")
    embedder = DenseEmbedder(
        api_key=settings.ZHIPUAI_API_KEY, 
        model_name=settings.EMBEDDING_MODEL_NAME
    )
    indexer = BM25Indexer()
    rewriter = QueryRewriter(api_key=settings.ZHIPUAI_API_KEY)
    
    # 2. 连接 Milvus
    print("2️⃣ 连接 Milvus...")
    connections.connect("default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    collection = Collection(settings.MILVUS_COLLECTION_NAME)
    collection.load()
    
    # 3. 初始化独立模块
    print("3️⃣ 初始化各个检索模块...")
    dense_retriever = DenseRetriever(collection, embedder)
    sparse_retriever = SparseRetriever(collection, indexer)
    rrf_fusion = RRFFusion(k=60)
    
    graph_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "topology_graph.json")
    topology_expander = TopologyExpander(collection, graph_path)
    
    # 测试 Query
    test_query = "查询包含'手机'关键字的商品中，当前库存量最多的前10个以及存放它们的仓库位置"
    print(f"\n💬 原始测试 Query: {test_query}")
    
    # 4. 执行改写
    enhanced_query = rewriter.rewrite(test_query)
    print(f"✨ 改写后 Query: {enhanced_query}\n")
    
    # 5. 执行双路召回
    print("🔍 执行双路召回 (Top-15)...")
    dense_hits = dense_retriever.search(enhanced_query, limit=15)
    sparse_hits = sparse_retriever.search(enhanced_query, limit=15)
    print(f"   Dense 命中 {len(dense_hits)} 条, Sparse 命中 {len(sparse_hits)} 条")
    
    # 6. RRF 融合
    print("⚖️ 执行 RRF 融合截断 (Top-10)...")
    fused_hits = rrf_fusion.fuse(dense_hits, sparse_hits, top_k=10)
    
    base_tables = {hit['table_name'] for hit in fused_hits}
    print(f"   融合后识别到的基础表: {base_tables}\n")
    
    # 7. 拓扑扩展与 DDL 组装
    print("🕸️ 执行拓扑扩展并生成 DDL Context...")
    final_ddl = topology_expander.expand_and_format_ddl(fused_hits)
    
    print("\n================ DDL PROMPT ================\n")
    print(final_ddl)
    print("\n============================================")

if __name__ == "__main__":
    main()
