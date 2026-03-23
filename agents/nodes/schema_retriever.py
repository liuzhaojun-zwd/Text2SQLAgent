import os
from pymilvus import Collection, connections
from text_to_sql.config import settings
from text_to_sql.agents.state import AgentState
from text_to_sql.knowledge_base.embedder import DenseEmbedder
from text_to_sql.knowledge_base.bm25_indexer import BM25Indexer
from text_to_sql.knowledge_base.query_rewriter import QueryRewriter
from text_to_sql.retrieval.dense import DenseRetriever
from text_to_sql.retrieval.sparse import SparseRetriever
from text_to_sql.retrieval.rrf import RRFFusion
from text_to_sql.retrieval.topology import TopologyExpander

def schema_retriever_node(state: AgentState) -> AgentState:
    """
    检索与拓扑扩展节点
    """
    user_query = state["user_query"]
    
    # 1. 准备组件
    embedder = DenseEmbedder(api_key=settings.ZHIPUAI_API_KEY, model_name=settings.EMBEDDING_MODEL_NAME)
    indexer = BM25Indexer()
    rewriter = QueryRewriter(api_key=settings.ZHIPUAI_API_KEY)
    
    try:
        connections.connect("default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
        collection = Collection(settings.MILVUS_COLLECTION_NAME)
        collection.load()
    except Exception as e:
        print(f"Schema Retriever: Milvus connection failed: {e}")
        state["ddl_context"] = ""
        return state
        
    dense_retriever = DenseRetriever(collection, embedder)
    sparse_retriever = SparseRetriever(collection, indexer)
    rrf_fusion = RRFFusion(k=60)
    
    # 找到 topology_graph.json 的路径 (在 text_to_sql 根目录)
    graph_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "topology_graph.json")
    topology_expander = TopologyExpander(collection, graph_path)
    
    # 2. 改写 Query
    enhanced_query = rewriter.rewrite(user_query)
    state["enhanced_query"] = enhanced_query
    
    # 3. 双路检索
    dense_hits = dense_retriever.search(enhanced_query, limit=15)
    sparse_hits = sparse_retriever.search(enhanced_query, limit=15)
    
    # 4. RRF 融合
    fused_hits = rrf_fusion.fuse(dense_hits, sparse_hits, top_k=10)
    
    # 5. 拓扑扩展拼装 DDL
    ddl_context = topology_expander.expand_and_format_ddl(fused_hits)
    state["ddl_context"] = ddl_context
    
    return state
