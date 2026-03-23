from typing import Tuple, Any, Optional, Dict
from .interceptors.syntax import SyntaxInterceptor
from .interceptors.permission import PermissionInterceptor
from .interceptors.performance import PerformanceInterceptor

class AuditorChain:
    """
    SQL 审计责任链入口，串联所有拦截器
    """
    def __init__(self, db_engine: Any = None, user_role: str = "default"):
        # 实例化各层拦截器
        self.syntax_interceptor = SyntaxInterceptor()
        self.permission_interceptor = PermissionInterceptor(user_role)
        self.performance_interceptor = PerformanceInterceptor(db_engine)
        
        # 构建责任链: 语法校验 -> 业务权限校验 -> 性能分析
        self.syntax_interceptor\
            .set_next(self.permission_interceptor)\
            .set_next(self.performance_interceptor)
            
        self.entry_interceptor = self.syntax_interceptor
        
        # 保存默认上下文配置
        self.default_context = {
            "role": user_role,
            "db_engine": db_engine
        }

    def audit(self, sql: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        执行审计流程
        :param sql: 待校验的 SQL 语句
        :param context: 动态上下文，可覆盖初始化时的默认配置（如 role, db_engine 等）
        :return: (is_passed: bool, error_message: str)
        """
        # 合并默认上下文与动态传入的上下文
        exec_context = self.default_context.copy()
        if context:
            exec_context.update(context)
            
        return self.entry_interceptor.handle(sql, exec_context)
