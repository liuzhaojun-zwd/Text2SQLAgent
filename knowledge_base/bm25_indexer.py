import jieba
from typing import List, Dict
import math
from collections import Counter

class BM25Indexer:
    """
    负责对中文字段注释进行分词并生成稀疏向量（BM25 词频权重视作简化版）。
    Milvus 2.4+ 的 SPARSE_FLOAT_VECTOR 要求输入为 {term_id: weight} 的字典形式，或 scipy.sparse.csr_matrix。
    这里使用基于 Hash 的词汇表编码（Hashing Trick）来生成简单的 term frequency / TF-IDF 稀疏表示。
    """
    def __init__(self, vocab_size: int = 30000):
        self.vocab_size = vocab_size
        # 为了提高分词准确性，可以加载自定义词典
        # jieba.load_userdict('custom_dict.txt')

    def tokenize(self, text: str) -> List[str]:
        """
        使用 jieba 对输入文本进行分词
        """
        # 过滤掉标点符号和空格
        words = jieba.lcut(text)
        return [w for w in words if w.strip() and not w in ".,;:!?'\"()[]{}<>`~@#$%^&*_-+=|\\/"]

    def _hash_word(self, word: str) -> int:
        """
        使用内置 hash 函数将词映射到 0 ~ vocab_size-1 之间
        """
        return abs(hash(word)) % self.vocab_size

    def generate_sparse_vector(self, text: str) -> Dict[int, float]:
        """
        将文本转换为稀疏向量格式，适配 Milvus 的输入要求
        这里采用简化的 TF 权重
        """
        words = self.tokenize(text)
        if not words:
            return {0: 1.0} # 避免空向量
            
        word_counts = Counter(words)
        total_words = len(words)
        
        sparse_vec = {}
        for word, count in word_counts.items():
            idx = self._hash_word(word)
            # 简单的 TF 计算: (词频 / 总词数)
            tf = count / total_words
            # 如果发生了 hash 冲突，简单地累加
            sparse_vec[idx] = sparse_vec.get(idx, 0.0) + tf
            
        return sparse_vec

    def generate_batch(self, texts: List[str]) -> List[Dict[int, float]]:
        """
        批量生成稀疏向量
        """
        return [self.generate_sparse_vector(t) for t in texts]
