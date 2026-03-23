import json
from typing import List, Dict, Any, Set
from collections import defaultdict
from pymilvus import Collection

class TopologyExpander:
    """
    负责执行拓扑感知补全：提取表名 -> 查询外键图谱 -> 拉取关联表全量字段 -> 按表分组拼装为完整 DDL
    """
    def __init__(self, collection: Collection, graph_path: str):
        """
        :param collection: 已经建立连接的 Milvus Collection 实例 (用于拉取表的全量字段)
        :param graph_path: topology_graph.json 文件的路径
        """
        self.collection = collection
        self.graph = []
        
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                self.graph = json.load(f)
        except Exception as e:
            print(f"Failed to load topology graph from {graph_path}: {e}")

    def _get_expanded_tables(self, base_tables: Set[str]) -> Set[str]:
        """根据外键图谱获取需要扩展的关联表"""
        expanded = set()
        
        # 解析图谱结构
        if isinstance(self.graph, dict):
            for source, target in self.graph.items():
                source_table = source.split('.')[0]
                target_table = target.split('.')[0]
                
                if source_table in base_tables and target_table not in base_tables:
                    expanded.add(target_table)
                elif target_table in base_tables and source_table not in base_tables:
                    expanded.add(source_table)
        elif isinstance(self.graph, list):
            for edge in self.graph:
                if isinstance(edge, dict):
                    source_table = edge.get("source_table")
                    target_table = edge.get("target_table")
                    
                    if source_table and target_table:
                        if source_table in base_tables and target_table not in base_tables:
                            expanded.add(target_table)
                        elif target_table in base_tables and source_table not in base_tables:
                            expanded.add(source_table)
                            
        return expanded

    def _fetch_table_schema_from_milvus(self, table_names: Set[str]) -> Dict[str, List[str]]:
        """从 Milvus 中拉取指定表的所有字段定义"""
        schema_dict = defaultdict(list)
        if not table_names or not self.collection:
            return schema_dict
            
        # 构建 expr
        tables_str = ", ".join([f"'{t}'" for t in table_names])
        expr = f"table_name in [{tables_str}]"
        
        try:
            # 取足够大的 limit 以确保能拉取到表的所有字段
            results = self.collection.query(
                expr=expr,
                output_fields=["table_name", "column_name", "text"],
                limit=1000
            )
            
            for hit in results:
                t_name = hit.get("table_name")
                text = hit.get("text", "")
                # 假设 text 包含了字段的完整 DDL 注释 (e.g., "id INT PRIMARY KEY COMMENT '...'")
                if text and text not in schema_dict[t_name]:
                    schema_dict[t_name].append(text)
        except Exception as e:
            print(f"Failed to fetch schema from Milvus: {e}")
            
        return schema_dict

    def expand_and_format_ddl(self, retrieved_hits: List[Dict[str, Any]]) -> str:
        """
        执行拓扑扩展并拼装 DDL
        :param retrieved_hits: 经过 RRF 融合后的 Top-K 检索结果
        :return: 格式化好的包含关联表的 DDL 字符串
        """
        if not retrieved_hits:
            return ""
            
        # 1. 提取基础表名
        base_tables = {hit["table_name"] for hit in retrieved_hits if "table_name" in hit}
        
        # 2. 查外键图谱，获取扩展表
        expanded_tables = self._get_expanded_tables(base_tables)
        
        # 合并所有需要拉取 schema 的表
        all_target_tables = base_tables.union(expanded_tables)
        
        # 3. 从 Milvus 拉取这些表的全量字段
        schema_dict = self._fetch_table_schema_from_milvus(all_target_tables)
        
        # 4. 拼装为完整的 DDL 字符串
        ddl_statements = []
        for table_name, columns in schema_dict.items():
            if not columns:
                continue
                
            # 标记是否是扩展进来的表，用于 Prompt 中的提示
            is_expanded = " (Expanded via Foreign Key)" if table_name in expanded_tables else ""
            
            # 格式化表结构
            table_ddl = f"CREATE TABLE {table_name}{is_expanded} (\n"
            # 为了美观，给每一列前面加缩进，并在末尾加逗号（除了最后一行）
            formatted_cols = []
            for col in columns:
                # 简单清理可能多余的空白符
                clean_col = " ".join(col.split())
                formatted_cols.append(f"  {clean_col}")
                
            table_ddl += ",\n".join(formatted_cols)
            table_ddl += "\n);"
            
            ddl_statements.append(table_ddl)
            
        # 用空行分隔不同的表
        return "\n\n".join(ddl_statements)
