import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML
from typing import Tuple, Optional, Any, Dict, List
from .base import BaseInterceptor

class PermissionInterceptor(BaseInterceptor):
    """
    第二层：业务权限校验
    根据用户角色、权限配置表，校验该用户是否有权访问 SQL 中涉及的表或敏感字段
    """
    def __init__(self, user_role: str = "default"):
        super().__init__()
        self.default_role = user_role
        
        # 简单的角色 -> 表访问控制列表 (ACL)
        self.acl = {
            "default": {
                "allowed": ["employees", "departments", "salaries", "projects"], # 允许访问的普通表
                "denied": ["admin_passwords", "system_config", "audit_logs"]     # 明确拒绝的敏感表
            },
            "admin": {
                "allowed": ["*"], # admin 拥有所有权限
                "denied": []
            }
        }

    def _extract_tables(self, sql: str) -> List[str]:
        """
        从 SQL 中粗略提取表名。
        这是一个简化的实现，依赖于寻找 FROM 和 JOIN 关键字后面的标识符。
        """
        tables = set()
        parsed = sqlparse.parse(sql)[0]
        
        # 标记是否已经遇到 FROM 或 JOIN
        from_seen = False
        
        for item in parsed.tokens:
            if item.is_whitespace:
                continue
            
            # 如果遇到 FROM 或 JOIN 关键字，标记并继续
            if item.ttype is Keyword and item.value.upper() in ("FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN"):
                from_seen = True
                continue
                
            if from_seen:
                # 遇到标识符列表 (如 FROM a, b)
                if isinstance(item, IdentifierList):
                    for identifier in item.get_identifiers():
                        tables.add(identifier.get_real_name().lower())
                    from_seen = False # 简单处理，提取完后重置
                # 遇到单个标识符
                elif isinstance(item, Identifier):
                    real_name = item.get_real_name()
                    if real_name:
                        tables.add(real_name.lower())
                    from_seen = False
                # 如果遇到其他关键字 (如 WHERE, GROUP BY)，则说明 FROM 阶段结束
                elif item.ttype is Keyword:
                    from_seen = False

        return list(tables)

    def check(self, sql: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        # 从上下文中获取角色，如果没传，则使用初始化时的默认角色
        current_role = (context.get("role") if context else None) or self.default_role
        
        # 获取该角色的 ACL 规则，如果角色不存在，退级为 default
        role_acl = self.acl.get(current_role, self.acl["default"])
        
        # Admin 拥有所有权限，直接放行
        if "*" in role_acl.get("allowed", []):
            return True, ""

        accessed_tables = self._extract_tables(sql)
        denied_tables = role_acl.get("denied", [])
        allowed_tables = role_acl.get("allowed", [])

        for table in accessed_tables:
            # 1. 检查是否在明确拒绝的名单中
            if table in denied_tables:
                return False, f"Permission Denied: 无权访问表 {table}"
            # 2. 检查是否在允许的名单中（白名单机制）
            if allowed_tables and table not in allowed_tables:
                return False, f"Permission Denied: 表 {table} 不在白名单中"
                
        return True, ""
