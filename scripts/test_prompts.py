import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zhipuai import ZhipuAI
from text_to_sql.config import settings

from text_to_sql.prompts.intent_align import get_intent_align_prompt
from text_to_sql.prompts.sql_generator import get_sql_generator_prompt
from text_to_sql.prompts.reflection import get_reflection_prompt
from text_to_sql.prompts.result_summary import get_result_summary_prompt

def call_llm(prompt_text):
    client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.EMBEDDING_MODEL_NAME.replace("embedding-3", "glm-4-flash"), # 用一个低成本的生成模型
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()

def main():
    print("🚀 开始测试提示词模板...")
    
    # 1. 测试意图解析 (Intent Align)
    print("\n" + "="*40)
    print("1️⃣ 测试意图解析 (Intent Align)")
    user_inputs = [
        "你好呀，今天天气不错",
        "我想看看上个月的离职员工平均薪水是多少？",
        "帮我查一下那个什么表的销售额"
    ]
    
    for query in user_inputs:
        print(f"\n💬 用户输入: {query}")
        prompt = get_intent_align_prompt(query)
        res = call_llm(prompt)
        print(f"🤖 LLM 输出:\n{res}")

    # 2. 测试 SQL 生成 (SQL Generator)
    print("\n" + "="*40)
    print("2️⃣ 测试 SQL 生成 (SQL Generator)")
    query = "查询上个月支付金额大于1000的订单及其关联的用户信息"
    ddl_context = """
CREATE TABLE orders (
  order_id bigint PRIMARY KEY,
  user_id bigint,
  total_amount decimal(10,2),
  status varchar(20),
  created_at datetime
);
CREATE TABLE users (
  user_id bigint PRIMARY KEY,
  username varchar(50)
);
    """
    prompt = get_sql_generator_prompt(query, ddl_context)
    print(f"💬 用户输入: {query}")
    res = call_llm(prompt)
    print(f"🤖 LLM 输出:\n{res}")
    
    # 3. 测试反思修复 (Reflection)
    print("\n" + "="*40)
    print("3️⃣ 测试反思修复 (Reflection)")
    error_msg = "Table 'users' doesn't have column 'name'"
    bad_sql = "SELECT username, name FROM users WHERE user_id = 1"
    prompt = get_reflection_prompt(query, ddl_context, bad_sql, error_msg)
    print(f"💬 错误信息: {error_msg}")
    res = call_llm(prompt)
    print(f"🤖 LLM 输出:\n{res}")
    
    # 4. 测试结果汇总 (Result Summary)
    print("\n" + "="*40)
    print("4️⃣ 测试结果汇总 (Result Summary)")
    execution_result = '[{"username": "张三", "total_amount": 1500.00}, {"username": "李四", "total_amount": 2000.50}]'
    good_sql = "SELECT u.username, o.total_amount FROM orders o JOIN users u ON o.user_id = u.user_id WHERE o.total_amount > 1000"
    prompt = get_result_summary_prompt(query, good_sql, execution_result)
    print(f"💬 执行结果: {execution_result}")
    res = call_llm(prompt)
    print(f"🤖 LLM 输出:\n{res}")

if __name__ == "__main__":
    main()
