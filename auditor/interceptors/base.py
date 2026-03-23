from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any, Dict

class BaseInterceptor(ABC):
    """
    SQL 审计拦截器抽象基类
    所有自定义的拦截规则都必须继承该类并实现 check 方法
    """
    
    def __init__(self):
        self.next_interceptor: Optional['BaseInterceptor'] = None

    def set_next(self, interceptor: 'BaseInterceptor') -> 'BaseInterceptor':
        """
        设置责任链的下一个拦截器
        """
        self.next_interceptor = interceptor
        return interceptor

    @abstractmethod
    def check(self, sql: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        校验 SQL
        :param sql: 待校验的 SQL 语句
        :param context: 审计上下文，用于传递角色、数据库引擎等额外信息
        :return: (is_passed: bool, error_message: str)
        """
        pass

    def handle(self, sql: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        按顺序执行拦截器校验
        """
        if context is None:
            context = {}
            
        is_passed, err_msg = self.check(sql, context)
        if not is_passed:
            return False, err_msg
            
        if self.next_interceptor:
            return self.next_interceptor.handle(sql, context)
            
        return True, "Success"
