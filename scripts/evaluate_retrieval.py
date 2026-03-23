import os
import sys
import json

# 确保能 import 到根目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_to_sql.knowledge_base.embedder import DenseEmbedder
from text_to_sql.knowledge_base.bm25_indexer import BM25Indexer
from text_to_sql.knowledge_base.retriever import HybridRetriever
from text_to_sql.knowledge_base.query_rewriter import QueryRewriter
from text_to_sql.config import settings

def main():
    print("🚀 开始评估检索召回率...")
    
    # 1. 初始化依赖组件
    print("1️⃣ 初始化 Embedder, Indexer 和 Rewriter...")
    embedder = DenseEmbedder(
        api_key=settings.ZHIPUAI_API_KEY, 
        model_name=settings.EMBEDDING_MODEL_NAME
    )
    indexer = BM25Indexer()
    rewriter = QueryRewriter(
        api_key=settings.ZHIPUAI_API_KEY
    )
    
    print("2️⃣ 连接 Milvus 初始化 Retriever...")
    graph_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "topology_graph.json")
    retriever = HybridRetriever(
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
        collection_name=settings.MILVUS_COLLECTION_NAME,
        embedder=embedder,
        indexer=indexer,
        graph_path=graph_path,
        rewriter=rewriter
    )
    
    # 2. 加载测试数据集
    dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../tests/retrieval_dataset.json")
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        print(f"3️⃣ 成功加载测试数据集，共 {len(dataset)} 条用例。")
    except Exception as e:
        print(f"❌ 加载测试数据集失败: {e}")
        return
        
    # 3. 执行评测
    print("4️⃣ 开始执行评测，计算 Top-5 召回率...")
    
    total_queries = len(dataset)
    table_hit_count = 0     # 只要召回了目标表中的任何一个字段，就算表召回
    total_table_recall = 0.0 # 累加每次的召回率求平均
    
    for i, case in enumerate(dataset):
        query = case["query"]
        ground_truth_tables = set(case["ground_truth_tables"])
        
        print(f"\n--- 测试用例 {i+1}/{total_queries} ---")
        print(f"Query: {query}")
        
        # 检索 Top-10 (放宽到 10，看外键扩展效果)
        results = retriever.retrieve(query, top_k=20)
        
        # 按照“表”粒度进行截断：
        # 我们按顺序遍历结果，收集出现的表，直到收集满 5 张表（即 Top-5 表）
        retrieved_tables = []
        for r in results:
            t_name = r["table_name"]
            if t_name not in retrieved_tables:
                retrieved_tables.append(t_name)
            if len(retrieved_tables) >= 5:
                break
                
        retrieved_tables_set = set(retrieved_tables)
        
        # 打印扩展信息辅助观察
        expanded_tables = set([r["table_name"] for r in results if r.get("is_expanded") and r["table_name"] in retrieved_tables_set])
        if expanded_tables:
            print(f"🔗 通过外键图谱额外扩展并在 Top-5 表中的有: {expanded_tables}")
        
        # 计算表召回率：召回的表集合 与 ground truth 的交集 / ground truth 数量
        table_recall_rate = len(ground_truth_tables.intersection(retrieved_tables_set)) / len(ground_truth_tables) if ground_truth_tables else 0
        total_table_recall += table_recall_rate
        
        if table_recall_rate == 1.0:
            table_hit_count += 1
            print(f"✅ 表全量召回成功 (100%) - 召回的表: {retrieved_tables}")
        else:
            missed_tables = ground_truth_tables - retrieved_tables_set
            print(f"❌ 表召回缺失: {missed_tables} (当前召回率: {table_recall_rate*100:.1f}%)")
            print(f"   实际召回的 Top-5 表为: {retrieved_tables}")
            
    # 4. 打印汇总报告
    print("\n" + "="*40)
    print("📊 检索召回率评测报告 (表级 Top-5)")
    print("="*40)
    print(f"总测试用例数: {total_queries}")
    print(f"完全召回所有目标表的用例数: {table_hit_count} ({(table_hit_count/total_queries)*100:.2f}%)")
    print(f"平均表召回率 (Average Table Recall): {(total_table_recall/total_queries)*100:.2f}%")
    print("="*40)

if __name__ == "__main__":
    main()
