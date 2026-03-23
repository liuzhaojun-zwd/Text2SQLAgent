from langgraph.graph import StateGraph, END
from text_to_sql.agents.state import AgentState
from text_to_sql.agents.nodes.intent_align import intent_align_node
from text_to_sql.agents.nodes.schema_retriever import schema_retriever_node
from text_to_sql.agents.nodes.sql_generator import sql_generator_node
from text_to_sql.agents.nodes.sql_executor import sql_executor_node
from text_to_sql.agents.nodes.reflection import reflection_node
from text_to_sql.agents.nodes.result_summary import result_summary_node

def route_after_intent(state: AgentState) -> str:
    """根据意图决定下一步"""
    intent = state.get("intent")
    if intent == "chat" or intent == "clarify":
        return END # 如果是聊天或需要追问，直接结束图流程
    return "schema_retriever"

def route_after_execute(state: AgentState) -> str:
    """根据执行结果决定下一步：成功去总结，失败去反思（限制次数）"""
    error = state.get("error_message")
    if not error:
        return "result_summary"
    
    # 如果有错误，判断是否超出重试次数
    retry_count = state.get("retry_count", 0)
    if retry_count >= 3:
        state["final_response"] = f"很抱歉，经过多次尝试，我仍然无法生成正确的查询。最后一次的错误是：{error}"
        return END
        
    return "reflection"

def create_agent_graph():
    """构建并编译 LangGraph 工作流"""
    workflow = StateGraph(AgentState)
    
    # 1. 添加所有节点
    workflow.add_node("intent_align", intent_align_node)
    workflow.add_node("schema_retriever", schema_retriever_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("sql_executor", sql_executor_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("result_summary", result_summary_node)
    
    # 2. 定义边 (Edges)
    # 入口节点
    workflow.set_entry_point("intent_align")
    
    # 条件路由：解析意图后
    workflow.add_conditional_edges(
        "intent_align",
        route_after_intent,
        {
            "schema_retriever": "schema_retriever",
            END: END
        }
    )
    
    # 线性流转
    workflow.add_edge("schema_retriever", "sql_generator")
    workflow.add_edge("sql_generator", "sql_executor")
    
    # 条件路由：执行 SQL 后
    workflow.add_conditional_edges(
        "sql_executor",
        route_after_execute,
        {
            "result_summary": "result_summary",
            "reflection": "reflection",
            END: END
        }
    )
    
    # 反思修复后重新尝试执行
    workflow.add_edge("reflection", "sql_executor")
    
    # 总结完成后结束
    workflow.add_edge("result_summary", END)
    
    # 3. 编译图
    app = workflow.compile()
    return app
