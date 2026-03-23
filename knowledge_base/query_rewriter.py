from zhipuai import ZhipuAI
import json

class QueryRewriter:
    """
    负责利用大模型对用户原始 Query 进行意图理解、关键词提取和同义词/业务黑话扩展
    """
    def __init__(self, api_key: str, model_name: str = "glm-4-flash"):
        self.client = ZhipuAI(api_key=api_key)
        self.model_name = model_name
        self.prompt_template = """
你是一个精通企业级数据库和业务系统的数据库专家。你的任务是将用户模糊、不准确的自然语言查询，改写为更丰富的检索查询词，以提高向量检索在数据库表结构（表名、字段名、注释）中的召回率。

用户的原始问题可能是包含“业务黑话”或“口语化”的表述（例如：“晋升记录”对应“promotion_records”，“售后”对应“after_sales”或“退换货”，“物流轨迹”对应“logistics_tracking”等）。

请对原始问题进行分析，并输出以下内容：
1. 提取核心关键词。
2. 补充可能的业务同义词（包括英文表名、字段名可能的命名，如 user, order, employee, department 等）。
3. 结合原始问题，生成一段扩充后的综合查询文本，用于直接送入向量数据库检索。

请仅返回 JSON 格式的数据，不要输出任何额外的解释文本。JSON 结构如下：
{{
    "keywords": ["关键词1", "关键词2"],
    "synonyms": ["同义词1", "同义词2", "英文词1", "英文词2"],
    "rewritten_query": "原始问题 + 核心关键词 + 业务同义词的综合文本段落"
}}

原始问题：{query}
"""

    def rewrite(self, query: str) -> str:
        """
        调用大模型改写 Query，返回增强后的查询文本
        如果调用失败，则返回原始 query，保证系统鲁棒性
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": self.prompt_template.format(query=query)}
                ],
                temperature=0.1,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 尝试解析 JSON
            # 兼容可能的 markdown 代码块包装
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()
                
            parsed_result = json.loads(result_text)
            rewritten_query = parsed_result.get("rewritten_query", query)
            
            return rewritten_query
            
        except Exception as e:
            print(f"Query Rewrite failed: {e}")
            return query
