"""助教提供：同一批中文片段的内存 BM25 基线，供受控教学实验。"""

import logging

import jieba
from rank_bm25 import BM25Okapi

jieba.setLogLevel(logging.ERROR)


class KeywordIndex:
    def __init__(self, chunks: list[dict]):
        if not chunks:
            raise ValueError("BM25 语料不能为空")
        self.chunks = chunks
        self.tokenizer = jieba.Tokenizer()
        tokens = [self.tokenize(chunk["content"]) for chunk in chunks]
        if not any(tokens):
            raise ValueError("语料中没有可索引的词")
        self.index = BM25Okapi(tokens, k1=1.5, b=0.75, epsilon=0.25)

    def tokenize(self, text: str) -> list[str]:
        return [token for token in self.tokenizer.lcut_for_search(text.casefold(), HMM=False)
                if token.isalnum()]

    def search(self, question: str, top_k: int) -> list[dict]:
        if top_k < 1:
            raise ValueError("top_k 必须至少为 1")
        tokens = self.tokenize(question)
        if not tokens:
            return []
        scores = self.index.get_scores(tokens)
        query_tokens = set(tokens)
        # 没有任何词项重合的片段不加入候选；不使用人为正确答案分数阈值。
        results = [
            {"chunk": chunk, "score": float(score)}
            for chunk, score, terms in zip(self.chunks, scores, self.index.doc_freqs)
            if query_tokens.intersection(terms)
        ]
        return sorted(results, key=lambda hit: hit["score"], reverse=True)[:top_k]
