"""spaCy NER + noun chunks + KeyBERT semantic ranking against bucket tokens.

Lazy model loading. YAKE fallback when KeyBERT unavailable.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_NLP = None
_KB = None

# Generic words to drop early
_STOP_TOKENS = {
    "home", "page", "menu", "about", "contact", "subscribe", "newsletter",
    "click", "here", "more", "learn", "site", "website", "navigation",
    "address", "email", "phone", "footer", "header", "search",
    "us", "you", "we", "our", "your", "they", "their",
}

_HEX_RE = re.compile(r"^#?[0-9a-f]{3,8}$", re.I)
_URL_RE = re.compile(r"https?://|www\.", re.I)


def _load_spacy():
    global _NLP
    if _NLP is not None:
        return _NLP
    try:
        import spacy
        try:
            _NLP = spacy.load("en_core_web_sm")
        except OSError:
            from spacy.cli import download
            download("en_core_web_sm")
            _NLP = spacy.load("en_core_web_sm")
    except ImportError:
        logger.warning("spacy not installed — falling back to regex-only extraction")
        _NLP = False
    return _NLP


def _load_keybert():
    global _KB
    if _KB is not None:
        return _KB
    try:
        from keybert import KeyBERT
        _KB = KeyBERT(model="all-MiniLM-L6-v2")
    except ImportError:
        logger.warning("keybert not installed — falling back to YAKE")
        _KB = False
    return _KB


def _normalize(s: str) -> str:
    s = s.strip().lower()
    return re.sub(r"\s+", " ", s)


def _filter_candidate(s: str) -> bool:
    s = _normalize(s)
    if len(s) < 3 or len(s) > 60:
        return False
    if s in _STOP_TOKENS:
        return False
    if _HEX_RE.match(s):
        return False
    if _URL_RE.search(s):
        return False
    if not re.search(r"[a-z]", s):
        return False
    return True


def _spacy_candidates(text: str) -> list[str]:
    nlp = _load_spacy()
    if not nlp:
        return []
    doc = nlp(text[:50_000])  # cap input
    cands: list[str] = []
    # Named entities (ORG, PRODUCT, GPE, FAC, EVENT, WORK_OF_ART, NORP)
    keep = {"ORG", "PRODUCT", "GPE", "FAC", "EVENT", "WORK_OF_ART", "NORP", "LOC"}
    for ent in doc.ents:
        if ent.label_ in keep:
            cands.append(ent.text)
    # Noun chunks
    for chunk in doc.noun_chunks:
        cands.append(chunk.text)
    return cands


def _yake_candidates(text: str, top_n: int = 40) -> list[tuple[str, float]]:
    try:
        import yake
    except ImportError:
        return []
    kw = yake.KeywordExtractor(lan="en", n=3, top=top_n, features=None)
    return [(k, score) for k, score in kw.extract_keywords(text)]


def _keybert_rank(text: str, bucket_tokens: list[str], candidates: list[str], top_k: int = 30) -> list[tuple[str, float]]:
    kb = _load_keybert()
    if not kb or not candidates:
        return [(c, 0.5) for c in candidates[:top_k]]
    # Use bucket tokens as a "query" anchor by concatenating
    seed = " ".join(bucket_tokens) if bucket_tokens else ""
    pool = list({_normalize(c) for c in candidates if _filter_candidate(c)})
    if not pool:
        return []
    # Rank candidates by similarity to (text + seed)
    anchor = (seed + " " + text[:2000]).strip() or text[:2000]
    try:
        ranked = kb.extract_keywords(
            anchor,
            candidates=pool,
            top_n=min(top_k, len(pool)),
            use_maxsum=False,
        )
        return ranked
    except Exception as exc:  # noqa: BLE001
        logger.warning("keybert rank failed: %s", exc)
        return [(c, 0.5) for c in pool[:top_k]]


def extract_keywords(
    text: str,
    bucket_tokens: list[str],
    top_k: int = 30,
) -> list[dict[str, Any]]:
    """Extract candidate keywords from text using spaCy + KeyBERT.

    Returns list of {keyword, score, source} sorted desc by score.
    """
    if not text:
        return []

    # Pull candidates from spaCy (entities + noun chunks)
    spacy_cands = _spacy_candidates(text)
    spacy_cands = [c for c in spacy_cands if _filter_candidate(c)]

    # Augment with YAKE keyphrases (free fallback)
    yake_cands = _yake_candidates(text, top_n=40)
    yake_terms = [k for k, _ in yake_cands if _filter_candidate(k)]

    all_cands = spacy_cands + yake_terms
    if not all_cands:
        return []

    ranked = _keybert_rank(text, bucket_tokens, all_cands, top_k=top_k)
    out = []
    seen: set[str] = set()
    for term, score in ranked:
        norm = _normalize(term)
        if norm in seen:
            continue
        seen.add(norm)
        out.append({
            "keyword": norm,
            "score": float(score),
            "source": "spacy+keybert" if norm in {_normalize(c) for c in spacy_cands} else "yake+keybert",
        })
    return out
