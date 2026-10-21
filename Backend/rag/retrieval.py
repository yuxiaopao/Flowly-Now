"""Deterministic Chinese/English keyword ranking and bounded text segmentation."""
import math
import re
from collections import Counter

from .constants import BM25_K1, BM25_B, TOKEN_PATTERN, BOUNDARY_SEPARATORS


def tokenize(text):
    tokens = re.findall(TOKEN_PATTERN, text.lower())
    # Chinese bigrams reduce accidental matches on frequent single characters.
    for run in re.findall(r'[\u3400-\u9fff]{2,}', text):
        tokens.extend(run[index:index + 2] for index in range(len(run) - 1))
    return tokens


def keyword_scores(query, chunks):
    query_terms = set(tokenize(query))
    if not query_terms or not chunks:
        return {}
    counts = [Counter(tokenize(chunk.content)) for chunk in chunks]
    lengths = [sum(count.values()) for count in counts]
    average = sum(lengths) / len(lengths) or 1
    frequencies = Counter(term for count in counts for term in count if term in query_terms)
    scores = {}
    for chunk, count, length in zip(chunks, counts, lengths):
        score = 0.0
        for term in query_terms & count.keys():
            idf = math.log(1 + (len(chunks) - frequencies[term] + 0.5) / (frequencies[term] + 0.5))
            tf = count[term]
            score += idf * tf * (BM25_K1 + 1) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * length / average))
        if score:
            # Bounded relevance score, not a probability or embedding cosine score.
            scores[str(chunk.id)] = score / (1 + score)
    return scores


def cosine_score(left, right):
    if len(left) != len(right):
        raise ValueError('索引向量维度与查询不一致，请重新处理文档。')
    denominator = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return sum(x * y for x, y in zip(left, right)) / denominator if denominator else 0.0


def split_text(text, size, overlap, strategy):
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError('分块大小必须为正数，且重叠必须小于分块大小。')
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if strategy == 'recursive' and end < len(text):
            for separator in BOUNDARY_SEPARATORS:
                boundary = text.rfind(separator, start + max(size // 2, overlap + 1), end)
                if boundary >= 0:
                    end = boundary + len(separator)
                    break
        content = text[start:end]
        if content.strip():
            yield content, start, end
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
