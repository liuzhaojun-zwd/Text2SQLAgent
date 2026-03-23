from langchain_core.prompts import PromptTemplate

RESULT_SUMMARY_PROMPT = PromptTemplate.from_template(
    """你是一个专业的数据分析师。你的任务是将数据库查询返回的原始 JSON 结果，转化为通俗易懂、结构清晰的自然语言商业报告。

用户的原始问题是：
{user_query}

执行的 SQL 语句是：
```sql
{sql_query}
```

数据库返回的原始数据（JSON格式）如下：
```json
{execution_result}
```

请根据以上信息，撰写一份简明扼要的商业报告给用户。
要求：
1. 语言要专业、友好，具有商业洞察力。
2. 将原始 JSON 数据转换为用户友好的 Markdown 表格格式进行展示，确保排版美观清晰。
3. 尝试从数据中提炼出核心结论或业务洞察。
4. 如果返回的数据为空或异常，请委婉地告知用户未查询到符合条件的数据。
"""
)

def get_result_summary_prompt(user_query: str, sql_query: str, execution_result: str) -> str:
    return RESULT_SUMMARY_PROMPT.format(
        user_query=user_query,
        sql_query=sql_query,
        execution_result=execution_result
    )
