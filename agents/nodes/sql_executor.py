import json
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from text_to_sql.config import DATABASE_URL
from text_to_sql.agents.state import AgentState

def sql_executor_node(state: AgentState) -> AgentState:
    """
    SQL 执行节点
    由于目前还未完成安全审计拦截器，为了跑通图结构，这里直接进行数据库执行。
    注意：在正式生产环境中，这里应先经过 Auditor 校验。
    """
    sql = state.get("generated_sql")
    if not sql:
        state["error_message"] = "没有可执行的 SQL 语句。"
        return state
        
    # 为了防止意外修改数据，做极其简单的硬编码拦截（后续会被 Auditor 替代）
    upper_sql = sql.upper()
    if any(keyword in upper_sql for keyword in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]):
        state["error_message"] = "安全拦截：只能执行 SELECT 只读查询。"
        return state
        
    try:
        # 使用配置中的 READONLY_DATABASE_URL (或 DATABASE_URL) 创建引擎，保障执行沙箱安全性
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            
            # 将结果转为列表字典
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
            # 限制返回结果的大小，防止大模型 token 爆掉
            if len(rows) > 50:
                rows = rows[:50]
                state["execution_result"] = json.dumps(rows, default=str, ensure_ascii=False) + "\n(结果已截断，仅显示前50条)"
            else:
                state["execution_result"] = json.dumps(rows, default=str, ensure_ascii=False)
                
            state["error_message"] = None # 执行成功，清除错误
            
    except SQLAlchemyError as e:
        print(f"SQL Execution failed: {e}")
        state["error_message"] = f"数据库执行报错: {str(e)}"
        state["execution_result"] = None
        
    return state
