import os
import sys

# 确保能 import 到根目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_to_sql.knowledge_base.ddl_extractor import DDLExtractor
from text_to_sql.knowledge_base.ddl_chunker import DDLChunker
from text_to_sql.knowledge_base.graph_builder import GraphBuilder
from text_to_sql.knowledge_base.embedder import DenseEmbedder
from text_to_sql.knowledge_base.bm25_indexer import BM25Indexer
from text_to_sql.knowledge_base.milvus_loader import MilvusLoader
from text_to_sql.config import settings

def main():
    print("🚀 开始构建离线知识库...")
    
    # 1. 抽取与切片
    print("1️⃣ 正在扫描数据库提取表结构...")
    extractor = DDLExtractor(
        host=settings.MYSQL_HOST,
        port=int(settings.MYSQL_PORT),
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db_name=settings.MYSQL_DB
    )
    schemas = extractor.extract_all()
    extractor.close()
    
    print("2️⃣ 正在按字段粒度进行切片...")
    chunker = DDLChunker()
    chunks = chunker.chunk_all(schemas)
    print(f"共切分出 {len(chunks)} 个字段 chunk。")
    
    # 2. 构建外键图谱
    print("3️⃣ 正在提取外键约束构建关系图谱...")
    graph_builder = GraphBuilder(
        host=settings.MYSQL_HOST,
        port=int(settings.MYSQL_PORT),
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db_name=settings.MYSQL_DB
    )
    graph = graph_builder.build_graph()
    
    # 保存到项目根目录下的 topology_graph.json
    graph_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "topology_graph.json")
    graph_builder.save_graph(graph, graph_path)
    graph_builder.close()
    print(f"提取到 {len(graph)} 条外键关系，已保存至 {graph_path}。")
    
    # 3. 向量化
    print("4️⃣ 正在生成稠密向量与 BM25 稀疏向量...")
    embedder = DenseEmbedder(
        api_key=settings.ZHIPUAI_API_KEY, 
        model_name=settings.EMBEDDING_MODEL_NAME
    )
    indexer = BM25Indexer()
    
    # 提取所有 text 用于批量生成稠密向量
    texts = [chunk["text"] for chunk in chunks]
    # 智谱 API 批量限制 64 条
    print("调用智谱 API 生成稠密向量...")
    dense_vectors = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        print(f"正在处理第 {i} 到 {i+len(batch_texts)} 条...")
        batch_vectors = embedder.embed_batch(batch_texts)
        dense_vectors.extend(batch_vectors)
    
    for i, chunk in enumerate(chunks):
        chunk["dense_vector"] = dense_vectors[i]
        chunk["sparse_vector"] = indexer.generate_sparse_vector(chunk["text"])
        
    # 4. 写入 Milvus
    print("5️⃣ 正在将数据写入 Milvus 并构建双索引...")
    loader = MilvusLoader(
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
        collection_name=settings.MILVUS_COLLECTION_NAME
    )
    loader.create_collection()
    loader.create_indexes()
    loader.insert_data(chunks)
    
    print("✅ 离线知识库构建完成！")

if __name__ == "__main__":
    main()
