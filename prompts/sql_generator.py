from langchain_core.prompts import PromptTemplate

# 原有的字符串模板升级为 LangChain PromptTemplate
SQL_GENERATOR_TEMPLATE = """你是一个精通 SQL 的数据库专家。你的任务是根据用户的自然语言查询和提供的数据库表结构上下文，生成一段精准、高效、符合语法的只读 SQL 语句。

【严格限制与生成规则】：
1. 只能使用在【数据库表结构上下文 (DDL)】中出现过的表和字段，严禁臆造不存在的列！如果某些表标注了 "(Expanded via Foreign Key)"，说明它们是外键关联表，你可以通过 JOIN 语句将它们与主表连接使用。
2. 只能生成只读查询（SELECT 语句），严禁生成 INSERT/UPDATE/DELETE/DROP/ALTER 等修改数据的语句。
3. 尽量编写高效的 SQL（如合理使用 JOIN、GROUP BY 和聚合函数）。
4. 如果用户的查询条件模糊，请根据 DDL 的注释或常识进行最合理的推测。
5. 最终结果必须只输出纯 SQL 代码。不要使用 Markdown 格式（严禁使用 ```sql 和 ``` 包裹），直接输出以 SELECT 开头的纯文本，不要包含任何多余的解释、问候或注释。

【数据库表结构上下文 (DDL)】：
以下是你唯一可以依赖的表和字段信息：
{ddl_context}
{few_shot_section}
【用户查询】：
{user_query}

现在，请直接输出纯 SQL 代码（无 Markdown，直接以 SELECT 开头）：
"""

sql_generator_prompt_template = PromptTemplate(
    input_variables=["user_query", "ddl_context", "few_shot_section"],
    template=SQL_GENERATOR_TEMPLATE
)

def get_sql_generator_prompt(user_query: str, ddl_context: str, few_shot_examples: str = "") -> str:
    """
    根据用户查询、DDL 上下文以及可选的 few-shot 示例生成 SQL Prompt。
    保持原有签名的前提下，通过默认参数支持 few-shot 扩展。
    """
    few_shot_section = ""
    if few_shot_examples:
        few_shot_section = f"\n【参考示例 (Few-Shot)】：\n{few_shot_examples}\n"
        
    return sql_generator_prompt_template.format(
        user_query=user_query,
        ddl_context=ddl_context,
        few_shot_section=few_shot_section
    )
