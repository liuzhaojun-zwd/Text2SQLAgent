import re
import sqlparse
from typing import Tuple, Optional, Any, Dict
from .base import BaseInterceptor

class SyntaxInterceptor(BaseInterceptor):
    """
    第一层：语法校验 + 禁止写操作（INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE 直接拒绝）
    使用 sqlparse 解析 AST，确保多语句注入和隐藏的非查询操作被拦截。
    """
    def __init__(self):
        super().__init__()
        # 严格禁止的 DML/DDL 关键字
        self.forbidden_keywords = {
            "INSERT", "UPDATE", "DELETE", "DROP", 
            "ALTER", "TRUNCATE", "REPLACE", "GRANT", "REVOKE",
            "CREATE", "MERGE"
        }

    def check(self, sql: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        if not sql or not sql.strip():
            return False, "Syntax Error: SQL 语句为空"

        try:
            # 解析 SQL 语句（处理多条用分号隔开的 SQL）
            parsed_statements = sqlparse.parse(sql)
        except Exception as e:
            return False, f"Syntax Error: 解析失败 ({str(e)})"

        if not parsed_statements:
            return False, "Syntax Error: 无效的 SQL 语句"
            
        if len(parsed_statements) > 1:
            # 只允许执行一条语句，防止注入 `SELECT * FROM a; DROP TABLE b;`
            return False, "Syntax Error: 禁止执行多条 SQL 语句"

        statement = parsed_statements[0]
        statement_type = statement.get_type()

        # 1. 检查根操作类型是否为 SELECT
        if statement_type != "SELECT" and statement_type != "UNKNOWN":
            return False, f"Syntax Error: 包含禁止的非查询操作: {statement_type}"

        # 2. 深入 AST 检查是否包含危险关键字
        # get_type() 有时可能不够准确（例如复杂子查询），这里结合 AST Token 遍历和关键字集合做双重保险
        tokens = [t for t in statement.flatten() if not t.is_whitespace]
        for token in tokens:
            # 如果 token 是关键字类型，检查是否在黑名单中
            if token.ttype in sqlparse.tokens.Keyword or token.ttype in sqlparse.tokens.Keyword.DML or token.ttype in sqlparse.tokens.Keyword.DDL:
                if token.value.upper() in self.forbidden_keywords:
                    return False, f"Syntax Error: 包含禁止的非查询操作: {token.value.upper()}"

        return True, ""
