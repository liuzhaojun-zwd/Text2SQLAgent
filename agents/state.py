from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict):
    """
    贯穿整个 Text-to-SQL 工作流的状态结构
    """
    # 原始用户输入
    user_query: str
    
    # 意图解析结果: query_data | clarify | chat
    intent: Optional[str]
    
    # 提取的实体
    entities: Optional[List[str]]
    
    # 改写后的 Query
    enhanced_query: Optional[str]
    
    # 检索到的 DDL 上下文
    ddl_context: Optional[str]
    
    # 大模型生成的 SQL
    generated_sql: Optional[str]
    
    # SQL 执行或审计的结果/报错信息
    error_message: Optional[str]
    
    # 数据库执行返回的 JSON 结果
    execution_result: Optional[str]
    
    # 当前反思重试的次数
    retry_count: int
    
    # 最终返回给用户的自然语言答复
    final_response: Optional[str]
