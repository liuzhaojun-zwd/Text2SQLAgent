from langchain_core.prompts import PromptTemplate

INTENT_ALIGN_PROMPT = """你是一个企业级数据助手的意图识别模块。请分析用户的输入，判断其真实意图。

请将用户的意图分类为以下三种之一：
1. "query_data": 用户希望查询、统计或分析数据库中的数据。
2. "clarify": 用户的话语含糊不清，或者缺少必要条件，需要向用户追问澄清。
3. "chat": 纯粹的闲聊、问候或与数据查询无关的对话。

如果意图是 "query_data"，请尽可能提取出其中的关键实体（如时间、人名、状态等）。

请严格以 JSON 格式输出，不要包含任何额外的解释说明或 Markdown 代码块标记（如 ```json ）。输出必须是一个纯净且合法的 JSON 字符串。格式要求如下：
{{
    "intent": "query_data" | "clarify" | "chat",
    "entities": ["实体1", "实体2"],
    "clarify_question": "如果是 clarify，这里填追问的问题，否则为空字符串",
    "chat_response": "如果是 chat，这里填回复内容，否则为空字符串"
}}

用户的输入是：
{user_input}"""

# 暴露 PromptTemplate 对象，便于在 LangGraph 或 LangChain LCEL 链中调用
INTENT_ALIGN_PROMPT_TEMPLATE = PromptTemplate.from_template(INTENT_ALIGN_PROMPT)

def get_intent_align_prompt(user_input: str) -> str:
    """
    为了保持向后兼容，保留原有的函数签名。
    """
    return INTENT_ALIGN_PROMPT_TEMPLATE.format(user_input=user_input)
