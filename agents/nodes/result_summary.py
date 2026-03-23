from zhipuai import ZhipuAI
from text_to_sql.config import settings
from text_to_sql.agents.state import AgentState
from text_to_sql.prompts.result_summary import get_result_summary_prompt

def result_summary_node(state: AgentState) -> AgentState:
    """
    结果汇总节点
    """
    user_query = state["user_query"]
    sql_query = state.get("generated_sql", "无 SQL")
    execution_result = state.get("execution_result", "未获取到数据")
    
    prompt = get_result_summary_prompt(user_query, sql_query, execution_result)
    
    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="glm-4-flash", # 总结结果不需要太强的逻辑推理，用快速模型即可
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        state["final_response"] = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Result summary failed: {e}")
        state["final_response"] = f"抱歉，在总结查询结果时发生了错误: {str(e)}"
        
    return state
