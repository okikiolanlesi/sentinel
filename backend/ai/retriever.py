"""
SentinelAI — Dynamic Few-Shot Retriever (RAG-Lite)
===================================================
At scan time, picks the K most similar examples from our 44-sample Nigerian
fraud dataset and injects them into the prompt as additional few-shot examples.

WHY: Static few-shot examples are good, but they may not match the specific
fraud variant being analysed. By dynamically selecting the most similar
examples to the input message, we give GPT highly relevant context for THAT
specific case — a form of in-context learning at runtime.

This uses TF-IDF + cosine similarity (no embedding API needed, runs locally,
zero added latency, deterministic).
"""

import json
import os
import re
from typing import List, Dict, Any
from functools import lru_cache


DATASET_PATH = os.path.join(os.path.dirname(__file__), "data", "nigerian_scam_dataset.json")


# ─────────────────────────────────────────────────────────────────────────────
# SIMPLE TF-IDF — no scikit-learn dependency
# ─────────────────────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[a-zA-Z₦]+|\d+", re.UNICODE)
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "to",
    "of", "in", "on", "for", "with", "at", "by", "from", "and", "or", "but",
    "if", "as", "this", "that", "these", "those", "i", "you", "your", "we",
    "our", "they", "their", "it", "its", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "can", "shall",
    "not", "no", "yes", "so", "up", "out", "into", "than", "then", "now",
}


def _tokenize(text: str) -> List[str]:
    """Lowercase tokenize, strip stopwords."""
    return [
        t.lower() for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOPWORDS and len(t) > 1
    ]


def _term_freq(tokens: List[str]) -> Dict[str, float]:
    """Compute term frequencies as a dict."""
    if not tokens:
        return {}
    n = len(tokens)
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    return {t: c / n for t, c in counts.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse term-frequency dicts."""
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[t] * b[t] for t in common)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ─────────────────────────────────────────────────────────────────────────────
# DATASET LOADING (cached)
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_dataset() -> List[Dict[str, Any]]:
    """Load and pre-tokenize the Nigerian scam dataset once."""
    if not os.path.exists(DATASET_PATH):
        return []

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data.get("samples", [])
    enriched = []
    for s in samples:
        content = s.get("content", "")
        tokens = _tokenize(content)
        enriched.append({
            **s,
            "_tokens": tokens,
            "_tf": _term_freq(tokens),
        })
    return enriched


def retrieve_similar_examples(
    query: str,
    k: int = 3,
    min_similarity: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Find the top-K most similar examples to the query message.

    Args:
        query: The message being analysed
        k: Number of examples to return
        min_similarity: Minimum cosine similarity to include

    Returns:
        List of example dicts (sorted by similarity, highest first)
    """
    dataset = _load_dataset()
    if not dataset:
        return []

    query_tf = _term_freq(_tokenize(query))
    if not query_tf:
        return []

    scored = []
    for sample in dataset:
        sim = _cosine(query_tf, sample["_tf"])
        if sim >= min_similarity:
            scored.append((sim, sample))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:k]]


def format_examples_for_prompt(examples: List[Dict[str, Any]]) -> str:
    """
    Format retrieved examples as few-shot examples for the system prompt.
    """
    if not examples:
        return ""

    parts = ["\n\n# DATASET MATCHES (most similar examples from labelled corpus)"]
    for i, ex in enumerate(examples, 1):
        # Build the canonical JSON output for this example
        canonical = {
            "risk_score": ex.get("risk_score"),
            "threat_level": ex.get("threat_level"),
            "flags": ex.get("flags", []),
            "action": ex.get("action"),
            "reasoning": ex.get("explanation", ""),
            "is_scam": ex.get("label") == "scam",
        }
        parts.append(
            f"\nMATCH {i} (id={ex.get('id')}, category={ex.get('category')}):\n"
            f'Message: "{ex.get("content", "")}"\n'
            f"Output: {json.dumps(canonical, ensure_ascii=False)}"
        )
    return "\n".join(parts)
