from typing import List, Dict, Any
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

class MilvusLoader:
    """
    负责管理 Milvus 的 Collection 并在建库阶段写入数据，构建双索引。
    支持 Milvus 2.4+ 的稠密和稀疏向量混合存储。
    """
    def __init__(self, host: str, port: str, collection_name: str):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.dim = 2048
        
        # 建立与 Milvus 的连接
        try:
            # 恢复为使用独立版 Milvus Server
            connections.connect("default", host=self.host, port=self.port)
            print(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}")
            raise
        self.collection = None

    def create_collection(self):
        """
        创建 Collection Schema 并构建索引
        """
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="table_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="column_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR)
        ]
        
        schema = CollectionSchema(fields, description="Schema knowledge base for Text2SQL")
        self.collection = Collection(self.collection_name, schema)
        print(f"Collection {self.collection_name} created.")

    def create_indexes(self):
        """
        为 Collection 构建双索引：
        - 稠密向量：HNSW 索引
        - 稀疏向量：SPARSE_INVERTED_INDEX 索引
        """
        if not self.collection:
            self.collection = Collection(self.collection_name)
            
        # 稠密向量索引
        dense_index = {
            "index_type": "AUTOINDEX",
            "metric_type": "IP",
            "params": {}
        }
        self.collection.create_index("dense_vector", dense_index)
        
        # 稀疏向量索引
        sparse_index = {
            "index_type": "SPARSE_INVERTED_INDEX",
            "metric_type": "IP"
        }
        self.collection.create_index("sparse_vector", sparse_index)
        print(f"Indexes created for {self.collection_name}.")

    def insert_data(self, records: List[Dict[str, Any]]):
        """
        将构建好的记录批量写入 Milvus
        """
        if not self.collection:
            self.collection = Collection(self.collection_name)
            
        # 将 records 转换为列式数据
        table_names = [r["table_name"] for r in records]
        column_names = [r["column_name"] for r in records]
        texts = [r["text"] for r in records]
        dense_vectors = [r["dense_vector"] for r in records]
        sparse_vectors = [r["sparse_vector"] for r in records]
        
        entities = [
            table_names,
            column_names,
            texts,
            dense_vectors,
            sparse_vectors
        ]
        
        insert_result = self.collection.insert(entities)
        self.collection.flush()
        print(f"Inserted {insert_result.insert_count} records into Milvus.")
