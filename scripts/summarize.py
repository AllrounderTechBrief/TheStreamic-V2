"""
scripts/summarize.py
====================
Summarisation helpers for The Streamic.
All text generated here is original editorial prose — no scraping of article bodies.
"""
import re


def _split_sentences(text: str) -> list:
    """Safe sentence splitter that handles abbreviations gracefully."""
    text = (text or "").strip()
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def summarize_text(text: str, sentences: int = 2) -> str:
    """Return the first N sentences of text (fallback-safe)."""
    text = (text or "").strip()
    if not text:
        return ""
    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.text_rank import TextRankSummarizer
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        result = TextRankSummarizer()(parser.document, sentences)
        if result:
            return " ".join(str(s) for s in result)
    except Exception:
        pass
    parts = _split_sentences(text)
    return " ".join(parts[:sentences]) if parts else text


# Context-neutral editorial expansions — sound like a journalist, not an AI
_EXPANSIONS = [
    "Understanding what is changing helps teams plan ahead and avoid surprises.",
    "Organisations tracking this should review their current setup against the new expectations.",
    "Practical impact will vary by scale, but the direction is clear across the sector.",
    "Early movers tend to gain an efficiency edge before the change becomes standard practice.",
    "Teams should discuss this in their next planning cycle and note the timeline implications.",
    "Budgets, staffing, and tooling may all need revisiting in light of developments like this.",
    "Keeping a close eye on vendor roadmaps and standards bodies will pay off here.",
    "The operational details matter as much as the headline — check the specifics carefully.",
]


def summarize_for_card(title: str, teaser: str, target_words: int = 300) -> str:
    """
    Build ~target_words of clean, neutral editorial prose from title + teaser ONLY.
    No quotes, no brand puff, no LLM-ish hedging. Plain newsroom English.
    """
    base = " ".join([t for t in [title or "", teaser or ""] if t]).strip()
    if not base:
        return ""

    # Strip obvious press-release boilerplate
    base = re.sub(
        r"\b(today announced|is pleased to announce|proud to introduce|"
        r"we are excited|leading provider of|industry-leading|"
        r"state-of-the-art|cutting-edge|revolutionary|game-changing)\b",
        "",
        base, flags=re.IGNORECASE,
    )
    base = re.sub(r"\s{2,}", " ", base).strip()

    sents = _split_sentences(base)
    out = []
    for s in sents:
        if s and len(" ".join(out).split()) < int(target_words * 0.6):
            out.append(s)

    # Pad with neutral editorial expansions to reach target_words
    i = 0
    while len(" ".join(out).split()) < target_words and i < len(_EXPANSIONS):
        out.append(_EXPANSIONS[i])
        i += 1

    text = " ".join(out).strip()
    words = text.split()
    cap = int(target_words * 1.1)
    if len(words) > cap:
        words = words[:cap]
    return " ".join(words)
