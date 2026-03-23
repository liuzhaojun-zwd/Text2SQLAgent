from typing import List, Dict, Any

class DDLChunker:
    """
    负责将提取的表结构数据，按【字段粒度】进行切片，并生成规范的文本描述。
    """
    def __init__(self):
        pass

    def chunk_table(self, table_name: str, table_comment: str, columns_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将单张表的 schema 列表转换为 field 级别的 chunk 列表。
        每个 chunk 必须包含 table_name, column_name, text 等。
        """
        chunks = []
        for col in columns_info:
            col_name = col['column_name']
            col_type = col['column_type']
            is_nullable = "" if col['is_nullable'] else " NOT NULL"
            comment = col['comment']
            
            # 如果字段没有注释，我们把表注释加进去补充上下文
            if not comment:
                comment = f"属于 {table_comment}" if table_comment else "无注释"
            
            # 组装文本: "{table_name}.{column_name} {column_type} [NOT NULL] COMMENT '{comment}'"
            # 为了更好的语义检索，我们在 text 中再自然语言化地补充一些上下文
            text = f"{table_name}.{col_name} {col_type}{is_nullable} COMMENT '{comment}'"
            
            chunks.append({
                "table_name": table_name,
                "column_name": col_name,
                "text": text,
                "column_type": col_type,
                "comment": comment
            })
            
        return chunks

    def chunk_all(self, all_schemas: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将全库的 schema 数据转化为所有 chunk 的平铺列表
        """
        all_chunks = []
        for table_name, schema_info in all_schemas.items():
            table_comment = schema_info.get("comment", "")
            columns = schema_info.get("columns", [])
            chunks = self.chunk_table(table_name, table_comment, columns)
            all_chunks.extend(chunks)
            
        return all_chunks
