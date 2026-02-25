"""
PDF에서 텍스트를 추출하고 조문 단위로 파싱하는 모듈.
조문 패턴: 제X조, 제X조의X
"""
import re
from typing import IO

import pdfplumber

ARTICLE_PATTERN = re.compile(r"^(제\s*\d+조(?:의\s*\d+)?)")
TITLE_PATTERN   = re.compile(r"제\s*\d+조(?:의\s*\d+)?\s*[（(]([^）)\n]+)[）)]")
TOC_PATTERN     = re.compile(r"[.·‥…]{3,}|\.{2,}\s*\d+\s*$")
PARAGRAPH_START = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]|^\d+\.\s|^[가나다라마바사아자차카타파하]\.\s")


def extract_text_by_page(pdf_file: IO[bytes]) -> list[tuple[int, str]]:
    pages = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append((i, text))
    except Exception as e:
        raise ValueError(f"PDF 텍스트 추출 실패: {e}") from e
    return pages


def _normalize_article_number(raw: str) -> str:
    return re.sub(r"\s+", "", raw)


def parse_articles(pages: list[tuple[int, str]]) -> list[dict]:
    all_lines: list[tuple[int, str]] = []
    for page_num, text in pages:
        for line in text.splitlines():
            all_lines.append((page_num, line))

    articles: list[dict] = []
    current: dict | None = None

    for page_num, line in all_lines:
        stripped = line.strip()
        if not stripped:
            if current:
                current["article_text"] += "\n"
            continue

        m = ARTICLE_PATTERN.match(stripped)
        if m:
            if current:
                current["article_text"] = current["article_text"].strip()
                articles.append(current)

            raw_number = m.group(1)
            article_number = _normalize_article_number(raw_number)
            title_m = TITLE_PATTERN.search(stripped)
            article_title = title_m.group(1).strip() if title_m else None

            current = {
                "article_number": article_number,
                "article_title": article_title,
                "article_text": stripped + "\n",
                "page_number": page_num,
            }
        else:
            if current:
                if PARAGRAPH_START.match(stripped):
                    current["article_text"] += "\n" + stripped
                else:
                    if current["article_text"].endswith("-"):
                        current["article_text"] = current["article_text"][:-1] + stripped
                    else:
                        current["article_text"] += " " + stripped

    if current:
        current["article_text"] = current["article_text"].strip()
        articles.append(current)

    return [a for a in articles if not _is_toc_entry(a)]


def _is_toc_entry(article: dict) -> bool:
    text = article["article_text"]
    if TOC_PATTERN.search(text):
        return True
    lines = [l for l in text.splitlines() if l.strip()]
    body = " ".join(lines[1:]).strip()
    if len(body) < 30:
        return True
    return False


def parse_pdf(pdf_file: IO[bytes]) -> list[dict]:
    pages = extract_text_by_page(pdf_file)
    return parse_articles(pages)


_ENACTED_PATTERNS = [
    re.compile(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*(?:부터\s*)?시행"),
    re.compile(r"시행일?\s*[：:\s]\s*(\d{4})[.\s]\s*(\d{1,2})[.\s]\s*(\d{1,2})"),
    re.compile(r"(\d{4})[.]\s*(\d{1,2})[.]\s*(\d{1,2})[.]?\s*시행"),
]


def extract_enacted_date(pdf_file: IO[bytes]) -> str | None:
    pdf_file.seek(0)
    pages = extract_text_by_page(pdf_file)
    full_text = "\n".join(text for _, text in pages)

    addendum_match = re.search(r"부\s*칙", full_text)
    search_text = full_text[addendum_match.start():] if addendum_match else full_text

    for pattern in _ENACTED_PATTERNS:
        m = pattern.search(search_text)
        if not m:
            m = pattern.search(full_text)
        if m:
            year, month, day = m.group(1), m.group(2), m.group(3)
            return f"{year}-{int(month):02d}-{int(day):02d}"

    return None
