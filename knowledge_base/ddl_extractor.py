from typing import List, Dict, Any
import pymysql

class DDLExtractor:
    """
    负责连接目标数据库，通过 information_schema 扫描所有表和字段。
    """
    def __init__(self, host: str, port: int, user: str, password: str, db_name: str):
        self.db_name = db_name
        self.connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    def get_all_tables(self) -> List[Dict[str, str]]:
        """
        获取数据库中的所有表名及其注释
        """
        query = f"""
            SELECT TABLE_NAME, TABLE_COMMENT 
            FROM information_schema.tables 
            WHERE table_schema = '{self.db_name}' AND table_type = 'BASE TABLE'
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取指定表的字段结构信息
        """
        query = f"""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT, COLUMN_KEY
            FROM information_schema.columns 
            WHERE table_schema = '{self.db_name}' AND table_name = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def extract_all(self) -> Dict[str, Dict[str, Any]]:
        """
        提取全库所有表的 schema 结构，包含表级注释和字段级详情
        返回结构: {
            "table_name": {
                "comment": "表注释",
                "columns": [{"column_name": "...", "column_type": "...", "comment": "...", ...}]
            }
        }
        """
        all_schemas = {}
        tables = self.get_all_tables()
        for t in tables:
            t_name = t['TABLE_NAME']
            t_comment = t['TABLE_COMMENT']
            columns = self.get_table_schema(t_name)
            
            formatted_columns = []
            for col in columns:
                formatted_columns.append({
                    "column_name": col['COLUMN_NAME'],
                    "data_type": col['DATA_TYPE'],
                    "column_type": col['COLUMN_TYPE'],
                    "is_nullable": col['IS_NULLABLE'] == 'YES',
                    "comment": col['COLUMN_COMMENT'],
                    "is_primary_key": col['COLUMN_KEY'] == 'PRI'
                })
                
            all_schemas[t_name] = {
                "comment": t_comment,
                "columns": formatted_columns
            }
            
        return all_schemas

    def close(self):
        if self.connection and self.connection.open:
            self.connection.close()
