import json
from zhipuai import ZhipuAI
from text_to_sql.config import settings
from text_to_sql.agents.state import AgentState
from text_to_sql.prompts.intent_align import get_intent_align_prompt

def intent_align_node(state: AgentState) -> AgentState:
    """
    意图解析节点
    """
    user_query = state["user_query"]
    prompt = get_intent_align_prompt(user_query)
    
    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=settings.EMBEDDING_MODEL_NAME.replace("embedding-3", "glm-4-flash"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        result_text = response.choices[0].message.content.strip()
        
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:-3].strip()
            
        parsed_result = json.loads(result_text)
        
        state["intent"] = parsed_result.get("intent", "query_data")
        state["entities"] = parsed_result.get("entities", [])
        
        if state["intent"] == "chat":
            state["final_response"] = parsed_result.get("chat_response", "你好，我是数据助手。")
        elif state["intent"] == "clarify":
            state["final_response"] = parsed_result.get("clarify_question", "请问您的具体需求是什么？")
            
    except Exception as e:
        print(f"Intent align failed: {e}")
        state["intent"] = "query_data" # 默认 fallback 到查数据
        
    return state
