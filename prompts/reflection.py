from langchain_core.prompts import PromptTemplate

REFLECTION_PROMPT = """你是一个高级 SQL 诊断与修复专家。你之前生成的 SQL 语句在执行或安全审计时失败了。请根据错误信息、原始查询意图和表结构上下文，重新修正该 SQL 语句。

【用户原始查询】：
{user_query}

【数据库表结构上下文 (DDL)】：
```sql
{ddl_context}
```

【你上次生成的 SQL 语句】：
```sql
{original_sql}
```

【失败原因/错误信息】：
{error_message}

【修复要求】：
1. 仔细阅读【失败原因/错误信息】，如果是因为字段不存在，请仔细检查【DDL】中真实的字段名。
2. 如果是因为语法错误（如缺少关键字、括号不匹配、类型不匹配等），请修正相应的语法。
3. 必须输出安全的只读 SELECT 查询，严禁任何修改数据的操作（如 INSERT, UPDATE, DELETE, DROP 等）。
4. 修复后的结果请只输出纯 SQL 代码，必须包裹在 ```sql 和 ``` 之间，不要包含任何多余的解释、问候或注释。

现在，请给出修复后的 SQL 语句："""

REFLECTION_PROMPT_TEMPLATE = PromptTemplate.from_template(REFLECTION_PROMPT)

def get_reflection_prompt(user_query: str, ddl_context: str, original_sql: str, error_message: str) -> str:
    return REFLECTION_PROMPT_TEMPLATE.format(
        user_query=user_query,
        ddl_context=ddl_context,
        original_sql=original_sql,
        error_message=error_message
    )
