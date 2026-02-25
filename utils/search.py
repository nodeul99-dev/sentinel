"""
키워드 검색 결과 처리 및 하이라이트 모듈.
"""
import re
import html

from db import search_articles

CATEGORIES = ["법령", "모범규준", "사규", "감독규정"]

CATEGORY_COLORS = {
    "법령":    "#15803d",
    "모범규준": "#047857",
    "사규":    "#0f766e",
    "감독규정": "#4d7c0f",
}


def run_search(keyword: str, selected_categories: list[str]) -> list[dict]:
    cats = selected_categories if selected_categories else None
    return search_articles(keyword, cats)


_MARK_STYLE = (
    'background:#a3e635;color:#14532d;'
    'padding:0 2px;border-radius:2px;font-weight:600;'
)


def _apply_highlight(escaped_text: str, keyword: str) -> str:
    if not keyword or not keyword.strip():
        return escaped_text
    pattern = re.compile(re.escape(html.escape(keyword)), re.IGNORECASE)
    return pattern.sub(
        lambda m: f'<mark style="{_MARK_STYLE}">{m.group()}</mark>',
        escaped_text,
    )


def highlight_snippet(text: str, keyword: str) -> str:
    return _apply_highlight(html.escape(text), keyword)


def highlight_text(text: str, keyword: str, max_chars: int = 400) -> str:
    if not keyword.strip():
        escaped = html.escape(text[:max_chars])
        return escaped + ("..." if len(text) > max_chars else "")

    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    match = pattern.search(text)

    if match:
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 300)
        snippet = text[start:end]
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
    else:
        snippet = text[:max_chars]
        prefix = ""
        suffix = "..." if len(text) > max_chars else ""

    return prefix + _apply_highlight(html.escape(snippet), keyword) + suffix


_PARAGRAPH_START = re.compile(
    r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]|^\d+\.\s|^[가나다라마바사아자차카타파하]\.\s"
)


def normalize_article_text(text: str) -> str:
    lines = text.splitlines()
    result = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if result:
                result += "\n"
            continue
        if not result:
            result = stripped
        elif _PARAGRAPH_START.match(stripped):
            result += "\n" + stripped
        else:
            if result.endswith("-"):
                result = result[:-1] + stripped
            else:
                result += " " + stripped
    return re.sub(r"[ \t]{2,}", " ", result)


def highlight_full_text(text: str, keyword: str) -> str:
    normalized = normalize_article_text(text)
    escaped = _apply_highlight(html.escape(normalized), keyword)
    return escaped.replace("\n", "<br>")


def category_badge(category: str) -> str:
    color = CATEGORY_COLORS.get(category, "#555")
    return (
        f'<span style="background:{color};color:white;'
        f'padding:2px 8px;border-radius:3px;font-size:0.72rem;'
        f'font-weight:600;margin-left:6px;">{html.escape(category)}</span>'
    )
