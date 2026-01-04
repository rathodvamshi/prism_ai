import re

from app.utils.preprocess import Preprocessor, preprocess, PLACEHOLDER_RE


def test_dual_text_and_entity_guard():
    p = Preprocessor()
    text = "Where’s my order ORD12345 for ₹500? Email test@gmail.com"

    out = p.preprocess(text)

    # Raw should remain untouched
    assert out["raw_text"] == text

    # Entities detected
    entities = out["entities"]
    assert "order_id" in entities and entities["order_id"][0] == "ORD12345"
    assert any(v.startswith("₹") or v.startswith("$") for v in entities.get("amount", []))
    assert "email" in entities and entities["email"][0] == "test@gmail.com"

    # Masked text should include placeholders, working_text should be restored
    masked = out["masked_text"]
    assert PLACEHOLDER_RE.search(masked)
    assert "ord12345" not in masked  # normalized lowercased + masked

    working = out["working_text"]
    assert "ORD12345" in working  # restored entity

    # Tokens present and placeholders respected in masked stage
    tokens = out["tokens"]
    assert isinstance(tokens, list) and len(tokens) > 0

    # Lemma tokens should skip placeholders (not lemmatize them)
    for t, lt in zip(tokens, out["lemma_tokens"]):
        if PLACEHOLDER_RE.fullmatch(t):
            assert lt == t


def test_contractions_and_whitespace_cleanup():
    p = Preprocessor()
    text = "  It's   DELIVERING   soon!  "
    out = p.preprocess(text)
    # Contraction expanded, case normalized, whitespace collapsed (in masked flow)
    assert "it is" in out["masked_text"]


def test_language_hint_simple():
    p = Preprocessor()
    assert p.language_hint("Track my order") == "en"
    assert p.language_hint("मेरा ऑर्डर कहाँ है") == "hi"
    assert p.language_hint("mera order kaha hai") in {"en", "hinglish"}


def test_module_level_function():
    out = preprocess("Track my order ORD9")
    assert out["raw_text"].startswith("Track")
    assert "order_id" in out["entities"]
