import unittest
from unittest.mock import MagicMock, patch
from text_to_sql.auditor.chain import AuditorChain
from text_to_sql.auditor.interceptors.syntax import SyntaxInterceptor
from text_to_sql.auditor.interceptors.permission import PermissionInterceptor
from text_to_sql.auditor.interceptors.performance import PerformanceInterceptor

class TestSyntaxInterceptor(unittest.TestCase):
    def setUp(self):
        self.interceptor = SyntaxInterceptor()

    def test_valid_select(self):
        sql = "SELECT id, name FROM users WHERE age > 18"
        passed, msg = self.interceptor.check(sql)
        self.assertTrue(passed)
        self.assertEqual(msg, "")

    def test_forbidden_write_operation(self):
        sql = "DELETE FROM users WHERE id = 1"
        passed, msg = self.interceptor.check(sql)
        self.assertFalse(passed)
        self.assertIn("DELETE", msg)

    def test_multiple_statements_injection(self):
        sql = "SELECT * FROM users; DROP TABLE admin;"
        passed, msg = self.interceptor.check(sql)
        self.assertFalse(passed)
        self.assertIn("多条", msg)

class TestPermissionInterceptor(unittest.TestCase):
    def setUp(self):
        self.interceptor = PermissionInterceptor(user_role="default")

    def test_default_role_allowed_table(self):
        sql = "SELECT * FROM employees"
        passed, msg = self.interceptor.check(sql, {"role": "default"})
        self.assertTrue(passed)

    def test_default_role_denied_table(self):
        sql = "SELECT * FROM admin_passwords"
        passed, msg = self.interceptor.check(sql, {"role": "default"})
        self.assertFalse(passed)
        self.assertIn("无权访问表", msg)

    def test_admin_role_access_all(self):
        sql = "SELECT * FROM admin_passwords"
        passed, msg = self.interceptor.check(sql, {"role": "admin"})
        self.assertTrue(passed)

class TestPerformanceInterceptor(unittest.TestCase):
    def test_full_table_scan_detection(self):
        # 模拟 SQLAlchemy 的 engine 和连接返回
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        
        # 模拟 EXPLAIN 返回结果 (字典形式的 keys 和 row 对应)
        # 假设查询触发了全表扫描，MySQL EXPLAIN 输出 type='ALL'
        mock_result = MagicMock()
        mock_result.keys.return_value = ["id", "select_type", "table", "type", "possible_keys", "key", "rows", "Extra"]
        # 第一行为一个返回数据的 row（以 tuple 模拟）
        mock_result.__iter__.return_value = [
            (1, "SIMPLE", "users", "ALL", None, None, 10000, "Using where")
        ]
        mock_conn.execute.return_value = mock_result

        interceptor = PerformanceInterceptor(db_engine=mock_engine)
        sql = "SELECT * FROM users"
        passed, msg = interceptor.check(sql)
        
        self.assertFalse(passed)
        self.assertIn("全表扫描", msg)
        self.assertIn("type=ALL", msg)

class TestAuditorChain(unittest.TestCase):
    def test_chain_success(self):
        chain = AuditorChain()
        # 默认上下文里没有 db_engine，会跳过 Performance 测试；默认 role 是 default，可以访问 employees
        sql = "SELECT id, name FROM employees"
        passed, msg = chain.audit(sql)
        self.assertTrue(passed)
        self.assertEqual(msg, "Success")

    def test_chain_fail_at_syntax(self):
        chain = AuditorChain()
        sql = "UPDATE employees SET salary = 9999"
        passed, msg = chain.audit(sql)
        self.assertFalse(passed)
        self.assertIn("Syntax Error", msg)

if __name__ == '__main__':
    unittest.main()
