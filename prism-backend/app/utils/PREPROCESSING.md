Preprocessing must preserve meaning, not rewrite user input.

Rules:
- Always keep raw input untouched
- Mask entities before normalization
- Use only semantic-safe transformations
- Lemmatize tokens, never rewrite sentences
- Phrase detection adds signal, never removes it
- No auto-translation, no paraphrasing

Pipeline:
1) Raw Store (immutable)
2) Entity Guard (mask)
3) Safe Normalization (NFKC, lowercase, contractions, whitespace)
4) Token + Phrase Extract
5) Lemma (skip entities)
6) Language Hint (passive)
7) Restore Entities
8) Intent + Entity Engine

Usage:

from app.utils.preprocess import preprocess

result = preprocess(user_input)

# Raw text is source of truth
raw = result["raw_text"]

# Working text is safe-normalized for intent/LLM
working = result["working_text"]

# Entities and hints
entities = result["entities"]
lang = result["language_hint"]

Integration pattern (FastAPI route):

_pre = preprocess(request.message)
raw = _pre["raw_text"]              # store/log
working = _pre["working_text"]     # intent + LLM
