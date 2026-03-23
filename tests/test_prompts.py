import sys
import os
import unittest

# Ensure the text_to_sql directory is in the python path for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from prompts.intent_align import get_intent_align_prompt
from prompts.sql_generator import get_sql_generator_prompt
from prompts.reflection import get_reflection_prompt
from prompts.result_summary import get_result_summary_prompt

class TestPrompts(unittest.TestCase):
    
    def test_intent_align_prompt(self):
        """Test intent_align prompt template formatting."""
        user_input = "查询昨天北京地区的订单总额"
        
        # Generate prompt
        result = get_intent_align_prompt(user_input)
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn(user_input, result)
        self.assertIn("query_data", result)
        self.assertIn("clarify", result)
        self.assertIn("chat", result)

    def test_sql_generator_prompt_without_few_shot(self):
        """Test sql_generator prompt template formatting without few-shot examples."""
        user_query = "查询昨天北京地区的订单总额"
        ddl_context = "CREATE TABLE orders (id INT, amount DECIMAL, city VARCHAR(50), order_date DATE);"
        
        # Generate prompt
        result = get_sql_generator_prompt(user_query=user_query, ddl_context=ddl_context)
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn(user_query, result)
        self.assertIn(ddl_context, result)
        self.assertNotIn("【参考示例 (Few-Shot)】", result)

    def test_sql_generator_prompt_with_few_shot(self):
        """Test sql_generator prompt template formatting with few-shot examples."""
        user_query = "查询昨天北京地区的订单总额"
        ddl_context = "CREATE TABLE orders (id INT, amount DECIMAL, city VARCHAR(50), order_date DATE);"
        few_shot_examples = "Q: 查询总数\\nA: SELECT COUNT(*) FROM orders;"
        
        # Generate prompt
        result = get_sql_generator_prompt(
            user_query=user_query, 
            ddl_context=ddl_context, 
            few_shot_examples=few_shot_examples
        )
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn(user_query, result)
        self.assertIn(ddl_context, result)
        self.assertIn(few_shot_examples, result)
        self.assertIn("【参考示例 (Few-Shot)】", result)

    def test_reflection_prompt(self):
        """Test reflection prompt template formatting."""
        user_query = "查询昨天北京地区的订单总额"
        ddl_context = "CREATE TABLE orders (id INT, amount DECIMAL, city VARCHAR(50), order_date DATE);"
        original_sql = "SELECT SUM(amount) FROM orders WHERE citty = '北京'"
        error_message = "Unknown column 'citty' in 'where clause'"
        
        # Generate prompt
        result = get_reflection_prompt(
            user_query=user_query,
            ddl_context=ddl_context,
            original_sql=original_sql,
            error_message=error_message
        )
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn(user_query, result)
        self.assertIn(ddl_context, result)
        self.assertIn(original_sql, result)
        self.assertIn(error_message, result)

    def test_result_summary_prompt(self):
        """Test result_summary prompt template formatting."""
        user_query = "查询昨天北京地区的订单总额"
        sql_query = "SELECT SUM(amount) as total_amount FROM orders WHERE city = '北京' AND order_date = '2023-10-24'"
        execution_result = '{"total_amount": 15000.50}'
        
        # Generate prompt
        result = get_result_summary_prompt(
            user_query=user_query,
            sql_query=sql_query,
            execution_result=execution_result
        )
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn(user_query, result)
        self.assertIn(sql_query, result)
        self.assertIn(execution_result, result)
        self.assertIn("商业报告", result)

if __name__ == '__main__':
    unittest.main()
