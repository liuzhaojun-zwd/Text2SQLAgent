from typing import Tuple, Any, Optional, Dict
from sqlalchemy import text
from .base import BaseInterceptor

class PerformanceInterceptor(BaseInterceptor):
    """
    第三层：执行性能预估
    通过 EXPLAIN 分析 SQL 计划，告警全表扫描或没有走索引的慢查询
    """
    def __init__(self, db_engine: Any = None):
        super().__init__()
        self.engine = db_engine

    def check(self, sql: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        # 从上下文中获取 engine（如果有），否则使用初始化时的 engine
        current_engine = (context.get("db_engine") if context else None) or self.engine
        
        if not current_engine:
            # 如果没有提供引擎，跳过性能检查
            return True, ""

        try:
            # 执行 EXPLAIN {sql}
            with current_engine.connect() as conn:
                explain_sql = f"EXPLAIN {sql}"
                result = conn.execute(text(explain_sql))
                
                # 获取列名并转换为小写以兼容不同数据库/驱动的返回结果
                keys = list(result.keys())
                keys_lower = [k.lower() for k in keys]
                
                for row in result:
                    # 将行数据转换为字典，键为小写
                    row_dict = {keys_lower[i]: val for i, val in enumerate(row)}
                    
                    # 检查是否为全表扫描 (MySQL 的 EXPLAIN 输出中 type 字段为 ALL)
                    if "type" in row_dict and str(row_dict["type"]).upper() == "ALL":
                        # 可以进一步判断扫描行数 (rows) 是否过大，这里简化为直接告警
                        table_name = row_dict.get("table", "Unknown Table")
                        return False, f"Performance Warning: 检测到表 '{table_name}' 的全表扫描 (type=ALL)，请添加索引或优化查询条件。"
                        
            return True, ""
        except Exception as e:
            # 如果 EXPLAIN 失败（可能是由于表不存在或语法错误在上一层没拦住），返回错误
            return False, f"Performance Evaluation Error: EXPLAIN 执行失败 - {str(e)}"
