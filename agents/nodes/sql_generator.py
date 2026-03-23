from zhipuai import ZhipuAI
from text_to_sql.config import settings
from text_to_sql.agents.state import AgentState
from text_to_sql.prompts.sql_generator import get_sql_generator_prompt

def sql_generator_node(state: AgentState) -> AgentState:
    """
    SQL 生成节点
    """
    user_query = state["user_query"]
    ddl_context = state.get("ddl_context", "")
    
    if not ddl_context:
        state["error_message"] = "未检索到相关的表结构上下文，无法生成 SQL。"
        return state
        
    prompt = get_sql_generator_prompt(user_query, ddl_context)
    
    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
    try:
        response = client.chat.completions.create(
            # 生成 SQL 建议使用稍微好一点的模型
            model="glm-4-air", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        result_text = response.choices[0].message.content.strip()
        
        # 提取 sql 代码块
        if "```sql" in result_text:
            sql = result_text.split("```sql")[1].split("```")[0].strip()
        elif "```" in result_text:
            sql = result_text.split("```")[1].strip()
        else:
            sql = result_text.strip()
            
        state["generated_sql"] = sql
        state["error_message"] = None # 清除之前的错误
        
    except Exception as e:
        print(f"SQL Generation failed: {e}")
        state["error_message"] = f"调用大模型生成 SQL 失败: {str(e)}"
        
    return state
