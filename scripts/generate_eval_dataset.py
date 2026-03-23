import json
import random

# 我们基于现有的 20 张表，用代码生成 100 个模拟测试用例
tables = [
    "users", "user_logs", "user_addresses", "categories", "products", 
    "inventory", "inventory_logs", "suppliers", "orders", "order_items", 
    "payments", "logistics_tracking", "after_sales", "reviews", "departments", 
    "employees", "salary_records", "attendance_records", "leave_records", "performance_reviews"
]

templates = [
    {"q": "统计所有{table}的数量", "sql": "SELECT COUNT(*) FROM {table};"},
    {"q": "查询最新的10条{table}记录", "sql": "SELECT * FROM {table} ORDER BY 1 DESC LIMIT 10;"},
    {"q": "找出关联{t1}和{t2}的数据", "sql": "SELECT * FROM {t1} t1 JOIN {t2} t2 ON t1.id = t2.id LIMIT 10;"},
    {"q": "按状态分组统计{table}的数量", "sql": "SELECT status, COUNT(*) FROM {table} GROUP BY status;"},
    {"q": "查询{table}中金额/数值大于100的记录", "sql": "SELECT * FROM {table} WHERE amount > 100 LIMIT 10;"}
]

dataset = []
for i in range(100):
    t = random.choice(templates)
    if "{t1}" in t["q"]:
        t1, t2 = random.sample(tables, 2)
        q = t["q"].format(t1=t1, t2=t2)
        sql = t["sql"].format(t1=t1, t2=t2)
    else:
        tb = random.choice(tables)
        q = t["q"].format(table=tb)
        # 简单修饰一下，防止语法错误
        sql_raw = t["sql"].format(table=tb)
        if "amount" in sql_raw and tb not in ["orders", "payments", "salary_records"]:
            sql = f"SELECT * FROM {tb} LIMIT 10;"
            q = f"查询{tb}的前10条记录"
        elif "status" in sql_raw and tb not in ["orders", "users", "payments", "leave_records", "attendance_records"]:
            sql = f"SELECT * FROM {tb} LIMIT 10;"
            q = f"查询{tb}的前10条记录"
        else:
            sql = sql_raw
            
    dataset.append({
        "id": i + 1,
        "query": q,
        "ground_truth_sql": sql
    })

with open("/root/data/text_to_sql/tests/text2sql_eval_dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=4)
print("100条评测数据集生成完毕！")
