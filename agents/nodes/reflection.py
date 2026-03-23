from zhipuai import ZhipuAI
from text_to_sql.config import settings
from text_to_sql.agents.state import AgentState
from text_to_sql.prompts.reflection import get_reflection_prompt

def reflection_node(state: AgentState) -> AgentState:
    """
    反思与自我修复节点
    """
    user_query = state["user_query"]
    ddl_context = state.get("ddl_context", "")
    original_sql = state.get("generated_sql", "")
    error_message = state.get("error_message", "")
    
    # 增加重试计数
    current_retry = state.get("retry_count", 0)
    state["retry_count"] = current_retry + 1
    
    print(f"⚠️ 正在进行第 {state['retry_count']} 次反思修复...")
    
    prompt = get_reflection_prompt(user_query, ddl_context, original_sql, error_message)
    
    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="glm-4-air",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        result_text = response.choices[0].message.content.strip()
        
        # 提取修复后的 sql
        if "```sql" in result_text:
            sql = result_text.split("```sql")[1].split("```")[0].strip()
        elif "```" in result_text:
            sql = result_text.split("```")[1].strip()
        else:
            sql = result_text.strip()
            
        state["generated_sql"] = sql
        state["error_message"] = None # 清除错误状态，准备重新执行
        
    except Exception as e:
        print(f"Reflection failed: {e}")
        state["error_message"] = f"反思修复环节调用大模型失败: {str(e)}"
        
    return state
