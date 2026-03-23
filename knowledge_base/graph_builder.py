import json
import pymysql
from typing import Dict, List, Tuple

class GraphBuilder:
    """
    负责提取表级外键约束，构建并存储独立的实体关系图谱。
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

    def extract_foreign_keys(self) -> List[Tuple[str, str, str, str]]:
        """
        从 information_schema 提取外键关系。
        返回列表元素示例: (src_table, src_column, target_table, target_column)
        """
        query = f"""
            SELECT 
                TABLE_NAME as src_table, 
                COLUMN_NAME as src_column, 
                REFERENCED_TABLE_NAME as target_table, 
                REFERENCED_COLUMN_NAME as target_column
            FROM 
                information_schema.KEY_COLUMN_USAGE
            WHERE 
                TABLE_SCHEMA = '{self.db_name}'
                AND REFERENCED_TABLE_NAME IS NOT NULL;
        """
        results = []
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                results.append((
                    row['src_table'], 
                    row['src_column'], 
                    row['target_table'], 
                    row['target_column']
                ))
        return results

    def build_graph(self) -> Dict[str, str]:
        """
        构建并返回外键图谱字典。
        结构示例: { "orders.user_id": "users.user_id" }
        """
        fks = self.extract_foreign_keys()
        graph = {}
        for src_table, src_column, target_table, target_column in fks:
            src_key = f"{src_table}.{src_column}"
            target_key = f"{target_table}.{target_column}"
            graph[src_key] = target_key
        return graph

    def save_graph(self, graph_data: Dict[str, str], file_path: str = "topology_graph.json"):
        """
        将图谱序列化并保存为 JSON 文件
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)

    def load_graph(self, file_path: str = "topology_graph.json") -> Dict[str, str]:
        """
        加载保存的图谱 JSON 文件
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def close(self):
        if self.connection and self.connection.open:
            self.connection.close()
