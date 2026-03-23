import os
import sys
import json
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymilvus import Collection, connections
from text_to_sql.config import settings, DATABASE_URL
from text_to_sql.knowledge_base.embedder import DenseEmbedder
from text_to_sql.knowledge_base.bm25_indexer import BM25Indexer
from text_to_sql.knowledge_base.query_rewriter import QueryRewriter
from text_to_sql.retrieval.dense import DenseRetriever
from text_to_sql.retrieval.sparse import SparseRetriever
from text_to_sql.retrieval.rrf import RRFFusion
from text_to_sql.retrieval.topology import TopologyExpander
from zhipuai import ZhipuAI
from text_to_sql.prompts.sql_generator import get_sql_generator_prompt

def execute_sql(engine, sql_str):
    """在数据库中执行 SQL，并返回规范化的结果（元组列表），若失败返回异常"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_str))
            # 为了忽略列名或列顺序的细微差异带来的干扰（部分业务场景可能只需对比行数据），
            # 这里将每一行转为 string 类型的 tuple，并排序。
            rows = result.fetchall()
            normalized_rows = [tuple(str(x) for x in row) for row in rows]
            # 对结果集进行排序，确保由于不包含 ORDER BY 导致的结果集乱序不被判定为错误
            return sorted(normalized_rows)
    except Exception as e:
        return str(e)

def generate_sql(query, retriever_components, llm_client):
    """执行在线检索 + SQL 生产的单步流程"""
    dense, sparse, rrf, topo, rewriter = retriever_components
    
    # 1. 改写
    enhanced_query = rewriter.rewrite(query)
    
    # 2. 检索
    dense_hits = dense.search(enhanced_query, limit=15)
    sparse_hits = sparse.search(enhanced_query, limit=15)
    
    # 3. 融合
    fused_hits = rrf.fuse(dense_hits, sparse_hits, top_k=10)
    
    # 4. 组装 DDL
    ddl_context = topo.expand_and_format_ddl(fused_hits)
    
    if not ddl_context:
        return "ERROR: No context found"
        
    # 5. 生成 SQL
    prompt = get_sql_generator_prompt(query, ddl_context)
    try:
        response = llm_client.chat.completions.create(
            model="glm-4-air",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        res_text = response.choices[0].message.content.strip()
        if "```sql" in res_text:
            sql = res_text.split("```sql")[1].split("```")[0].strip()
        elif "```" in res_text:
            sql = res_text.split("```")[1].strip()
        else:
            sql = res_text.strip()
        return sql
    except Exception as e:
        return f"ERROR: LLM failed - {str(e)}"

def main():
    print("🚀 初始化 Text2SQL 执行准确率评测环境...")
    
    # 初始化 MySQL 引擎
    engine = create_engine(DATABASE_URL)
    
    # 初始化组件
    llm_client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
    embedder = DenseEmbedder(api_key=settings.ZHIPUAI_API_KEY, model_name=settings.EMBEDDING_MODEL_NAME)
    indexer = BM25Indexer()
    rewriter = QueryRewriter(api_key=settings.ZHIPUAI_API_KEY)
    
    connections.connect("default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    collection = Collection(settings.MILVUS_COLLECTION_NAME)
    collection.load()
    
    dense_retriever = DenseRetriever(collection, embedder)
    sparse_retriever = SparseRetriever(collection, indexer)
    rrf_fusion = RRFFusion(k=60)
    
    graph_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "topology_graph.json")
    topology_expander = TopologyExpander(collection, graph_path)
    
    retriever_components = (dense_retriever, sparse_retriever, rrf_fusion, topology_expander, rewriter)
    
    # 读取数据集
    dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../tests/text2sql_eval_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    total = len(dataset)
    exec_success = 0  # 生成的 SQL 在数据库中能成功执行的次数
    exact_match = 0   # 执行结果与 Ground Truth SQL 完全一致的次数
    
    print(f"✅ 环境准备完毕，开始评测 {total} 条数据...\n")
    
    for i, item in enumerate(dataset):
        query = item["query"]
        gt_sql = item["ground_truth_sql"]
        
        print(f"[{i+1}/{total}] Q: {query}")
        
        # 1. 生成 SQL
        generated_sql = generate_sql(query, retriever_components, llm_client)
        
        if generated_sql.startswith("ERROR:"):
            print(f"   ❌ 生成失败: {generated_sql}")
            continue
            
        # 2. 执行两边的 SQL
        gt_result = execute_sql(engine, gt_sql)
        gen_result = execute_sql(engine, generated_sql)
        
        # 3. 对比判断
        if isinstance(gen_result, str):
            # 返回字符串说明是捕获到的执行错误
            print(f"   ❌ 执行失败 (语法/字段错误): {gen_result[:100]}...")
        else:
            exec_success += 1
            if gen_result == gt_result:
                exact_match += 1
                print("   ✅ 执行成功且结果一致 (Exact Match)")
            else:
                print("   ⚠️ 执行成功但结果不一致")
                
        time.sleep(1) # 略微等待，避免触发大模型频率限制
        
    # 打印最终报告
    print("\n" + "="*40)
    print("📊 Text-to-SQL 评测报告")
    print("="*40)
    print(f"总测试用例数: {total}")
    print(f"执行成功率 (Execution Success Rate): {exec_success}/{total} ({exec_success/total*100:.2f}%)")
    print(f"结果一致率 (Execution Accuracy): {exact_match}/{total} ({exact_match/total*100:.2f}%)")
    print("="*40)

if __name__ == "__main__":
    main()
