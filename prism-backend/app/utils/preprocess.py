from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Tuple, Iterable


PLACEHOLDER_RE = re.compile(r"__([A-Z_]+)_(\d+)__")


@dataclass
class EntitySpan:
    kind: str
    value: str
    start: int
    end: int
    placeholder: str


class Preprocessor:
    """
    Safe, fast, entity-aware preprocessing pipeline.

    Core principles implemented:
    - Dual text: keep `raw_text` untouched; operate on `working_text`.
    - Mask entities before normalization; restore after.
    - Only apply semantic-safe transformations (NFKC, lowercase, contractions, whitespace).
    - Lemmatize tokens in safe mode; skip entity tokens.
    - Phrase detection adds signal without altering input.
    - Language hint is passive (no translation).

    Target: sub-millisecond to a few milliseconds typical.
    """

    def __init__(self) -> None:
        # Precompiled lightweight regex patterns for common entities
        self._entity_patterns: List[Tuple[str, re.Pattern[str]]] = [
            ("email", re.compile(r"(?i)\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
            ("order_id", re.compile(r"\bORD\d+\b")),
            ("amount", re.compile(r"(?:₹|rs\.?|inr\s?)\s?\d+(?:[.,]\d+)?|\$\s?\d+(?:[.,]\d+)?", re.IGNORECASE)),
            ("phone", re.compile(r"\b(?:\+?\d[\d\s-]{7,}\d)\b")),
            ("url", re.compile(r"https?://[^\s]+")),
        ]

        # Very small contraction map (safe expansions)
        self._contractions: Dict[str, str] = {
            "can't": "cannot",
            "won't": "will not",
            "n't": " not",
            "i'm": "i am",
            "it's": "it is",
            "that's": "that is",
            "there's": "there is",
            "what's": "what is",
            "who's": "who is",
            "let's": "let us",
            "i've": "i have",
            "we've": "we have",
            "i'd": "i would",
            "you'd": "you would",
            "they'd": "they would",
            "i'll": "i will",
            "you'll": "you will",
            "they'll": "they will",
            "we're": "we are",
            "you're": "you are",
            "they're": "they are",
        }

        # Tiny lemma overrides for frequent commerce/chat verbs
        self._lemma_map: Dict[str, str] = {
            "ordered": "order",
            "orders": "order",
            "ordering": "order",
            "delivered": "deliver",
            "delivering": "deliver",
            "delivers": "deliver",
            "tracking": "track",
            "tracked": "track",
            "tracks": "track",
            "refunded": "refund",
            "refunds": "refund",
            "returning": "return",
            "returns": "return",
            "cancelled": "cancel",
            "canceled": "cancel",
            "cancelling": "cancel",
            "shipped": "ship",
            "shipping": "ship",
        }

        # Small set to hint Hinglish
        self._hinglish_markers = {"kya", "hai", "nahi", "mera", "meri", "tum", "ka", "ki", "se"}

    # -------- Entity detection and masking --------
    def detect_entities(self, text: str) -> List[EntitySpan]:
        spans: List[EntitySpan] = []
        taken: List[Tuple[int, int]] = []

        def overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
            return not (a[1] <= b[0] or b[1] <= a[0])

        counters: Dict[str, int] = {}
        for kind, pattern in self._entity_patterns:
            for m in pattern.finditer(text):
                start, end = m.span()
                if any(overlaps((start, end), t) for t in taken):
                    continue
                counters[kind] = counters.get(kind, 0) + 1
                placeholder = f"__{kind.upper()}_{counters[kind]}__"
                spans.append(EntitySpan(kind=kind, value=m.group(0), start=start, end=end, placeholder=placeholder))
                taken.append((start, end))
        # Sort by start for stable masking
        spans.sort(key=lambda s: s.start)
        return spans

    def mask_entities(self, text: str, spans: List[EntitySpan]) -> Tuple[str, Dict[str, str]]:
        if not spans:
            return text, {}
        out = []
        last = 0
        mapping: Dict[str, str] = {}
        for s in spans:
            out.append(text[last:s.start])
            out.append(s.placeholder)
            mapping[s.placeholder] = s.value
            last = s.end
        out.append(text[last:])
        return "".join(out), mapping

    def restore_entities(self, text: str, mapping: Dict[str, str]) -> str:
        if not mapping:
            return text
        def repl(m: re.Match[str]) -> str:
            key = m.group(0)
            return mapping.get(key, key)
        return PLACEHOLDER_RE.sub(repl, text)

    # -------- Safe normalization --------
    def _unicode_nfkc(self, text: str) -> str:
        return unicodedata.normalize("NFKC", text)

    def _lowercase_non_placeholders(self, text: str) -> str:
        parts: List[str] = []
        idx = 0
        for m in PLACEHOLDER_RE.finditer(text):
            if m.start() > idx:
                parts.append(text[idx:m.start()].lower())
            parts.append(m.group(0))  # keep placeholder as-is
            idx = m.end()
        if idx < len(text):
            parts.append(text[idx:].lower())
        return "".join(parts)

    def _expand_contractions(self, text: str) -> str:
        # Apply longest keys first to avoid partial overlaps
        items = sorted(self._contractions.items(), key=lambda x: -len(x[0]))
        def repl_segment(seg: str) -> str:
            s = seg
            for k, v in items:
                s = re.sub(rf"\b{re.escape(k)}\b", v, s)
            return s
        out: List[str] = []
        idx = 0
        for m in PLACEHOLDER_RE.finditer(text):
            if m.start() > idx:
                out.append(repl_segment(text[idx:m.start()]))
            out.append(m.group(0))
            idx = m.end()
        if idx < len(text):
            out.append(repl_segment(text[idx:]))
        return "".join(out)

    def _cleanup_whitespace(self, text: str) -> str:
        # Collapse whitespace runs to single spaces and trim
        return re.sub(r"\s+", " ", text).strip()

    # -------- Tokenization and phrases --------
    def tokenize(self, text: str) -> List[str]:
        # Simple whitespace tokenization
        if not text:
            return []
        return text.split()

    def phrases(self, tokens: List[str], n_values: Iterable[int] = (2, 3)) -> List[str]:
        out: List[str] = []
        for n in n_values:
            if len(tokens) < n:
                continue
            for i in range(len(tokens) - n + 1):
                out.append(" ".join(tokens[i:i + n]))
        return out

    # -------- Safe lemmatization (skip entities) --------
    def lemmatize_tokens(self, tokens: List[str]) -> List[str]:
        lemmas: List[str] = []
        for t in tokens:
            if PLACEHOLDER_RE.fullmatch(t):
                lemmas.append(t)
                continue
            lt = self._lemma_token(t)
            lemmas.append(lt)
        return lemmas

    def _lemma_token(self, token: str) -> str:
        if token in self._lemma_map:
            return self._lemma_map[token]
        # Conservative suffix rules (safe mode):
        # Only apply if token length reasonably long to avoid harming short words.
        t = token
        if len(t) > 5 and t.endswith("ing"):
            return t[:-3]
        if len(t) > 4 and t.endswith("ed"):
            return t[:-2]
        if len(t) > 4 and t.endswith("es"):
            return t[:-2]
        if len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
            return t[:-1]
        return t

    # -------- Language hint (passive) --------
    def language_hint(self, text: str) -> str:
        # Heuristic: Devanagari => hi; Latin with Hinglish markers => hinglish; else en
        for ch in text:
            cp = ord(ch)
            if 0x0900 <= cp <= 0x097F:
                return "hi"
        toks = {t.lower() for t in self.tokenize(text)}
        if any(w in toks for w in self._hinglish_markers):
            return "hinglish"
        return "en"

    # -------- Public API --------
    def preprocess(self, user_input: str) -> Dict[str, object]:
        raw_text = user_input

        # 1) Detect + mask entities
        spans = self.detect_entities(raw_text)
        masked_text, mapping = self.mask_entities(raw_text, spans)

        # 2) Safe normalization on working_text only
        working = self._unicode_nfkc(masked_text)
        working = self._lowercase_non_placeholders(working)
        working = self._expand_contractions(working)
        working = self._cleanup_whitespace(working)

        # 3) Tokens, phrases, lemmas (skip placeholders)
        tokens = self.tokenize(working)
        phrases = self.phrases(tokens)
        lemma_tokens = self.lemmatize_tokens(tokens)

        # 4) Passive language hint
        lang = self.language_hint(raw_text)

        # 5) Restore entities into working text (final handoff to intent engine)
        restored_working = self.restore_entities(working, mapping)

        # Summarize entities as dict: kind -> [values]
        entities: Dict[str, List[str]] = {}
        for s in spans:
            entities.setdefault(s.kind, []).append(s.value)

        return {
            "raw_text": raw_text,
            "working_text": restored_working,
            "masked_text": working,  # masked+normalized (for debug/audit)
            "entities": entities,
            "entity_spans": [s.__dict__ for s in spans],
            "placeholders": mapping,
            "language_hint": lang,
            "tokens": tokens,
            "lemma_tokens": lemma_tokens,
            "phrases": phrases,
        }


# Module-level convenience function
_DEFAULT = Preprocessor()


def preprocess(user_input: str) -> Dict[str, object]:
    return _DEFAULT.preprocess(user_input)
