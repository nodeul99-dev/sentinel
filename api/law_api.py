"""
법제처 국가법령정보 오픈API 연동 모듈 (law_api.py).

사용하는 API: https://open.law.go.kr/LSO/openApi/
- 법률·시행령: getMOLSLaw.do
- 행정규칙(감독규정): getMOLSAdmRul.do

환경변수 LAW_API_KEY (.env)에 법제처 API 키를 설정해야 합니다.
키 발급: https://open.law.go.kr/LSO/main.do → 오픈API 신청
"""
import re
import xml.etree.ElementTree as ET
from typing import Optional

import requests

from config import LAW_API_KEY
from db import upsert_document, insert_articles, update_article_count

_PARAGRAPH_START = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]|^\d+\.\s|^[가나다라마바사아자차카타파하]\.\s")


def _normalize_law_text(text: str) -> str:
    lines = text.splitlines()
    result = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not result:
            result = stripped
        elif _PARAGRAPH_START.match(stripped):
            result += "\n" + stripped
        else:
            result += " " + stripped
    result = re.sub(r"[ \t]{2,}", " ", result)
    return result


# ── 크롤링 대상 법령 목록 ───────────────────────────────────────────────────
MANAGED_LAWS = [
    {
        "name":     "자본시장과 금융투자업에 관한 법률",
        "category": "법령",
        "type":     "law",
    },
    {
        "name":     "자본시장과 금융투자업에 관한 법률 시행령",
        "category": "법령",
        "type":     "law",
    },
    {
        "name":     "금융투자업규정",
        "category": "감독규정",
        "type":     "admrul",
    },
    {
        "name":     "금융투자업 감독규정",
        "category": "감독규정",
        "type":     "admrul",
    },
]


def _get_endpoint(law_type: str) -> str:
    if law_type == "admrul":
        return "https://open.law.go.kr/LSO/openApi/getMOLSAdmRul.do"
    return "https://open.law.go.kr/LSO/openApi/getMOLSLaw.do"


def fetch_law_articles(
    law_name: str, law_type: str = "law"
) -> tuple[list[dict], Optional[str]]:
    """
    법제처 API로 조문 목록과 시행일을 수신.

    Returns: (articles, effective_date)
    Raises: ValueError | requests.RequestException | ET.ParseError
    """
    if not LAW_API_KEY:
        raise ValueError(
            "LAW_API_KEY가 설정되어 있지 않습니다.\n"
            ".env 파일에 LAW_API_KEY=<발급받은키> 를 추가해주세요."
        )

    endpoint = _get_endpoint(law_type)
    params = {
        "OC":     LAW_API_KEY,
        "target": law_type,
        "type":   "XML",
        "query":  law_name,
    }

    resp = requests.get(endpoint, params=params, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)

    effective_date = (
        root.findtext(".//시행일")
        or root.findtext(".//공포일")
        or root.findtext(".//법령정보/시행일")
    )

    articles = []
    for article in root.iter("조문"):
        text = article.findtext("조문내용") or ""
        if not text.strip():
            continue
        articles.append({
            "article_number": article.findtext("조문번호") or "",
            "article_title":  article.findtext("조문제목") or "",
            "article_text":   _normalize_law_text(text),
            "page_number":    None,
        })

    return articles, effective_date


def crawl_single_law(law_info: dict) -> tuple[bool, str]:
    """
    단일 법령을 API로 수신하여 DB에 저장.

    Returns: (success, message)
    """
    try:
        articles, effective_date = fetch_law_articles(
            law_info["name"], law_info["type"]
        )

        if not articles:
            return False, f"⚠️ {law_info['name']}: 조문을 가져오지 못했습니다 (0개 수신)."

        doc_id = upsert_document(
            doc_name=law_info["name"],
            doc_category=law_info["category"],
            filename="",
            enacted_date=effective_date,
            source_type="crawler",
        )
        insert_articles(doc_id, articles)
        update_article_count(doc_id, len(articles))

        date_str = effective_date or "날짜 미상"
        return True, f"✅ {law_info['name']} — {len(articles)}개 조문 (시행일: {date_str})"

    except ValueError as e:
        return False, f"❌ {law_info['name']}: {e}"
    except requests.RequestException as e:
        return False, f"❌ {law_info['name']}: 네트워크 오류 — {e}"
    except ET.ParseError as e:
        return False, f"❌ {law_info['name']}: 응답 파싱 오류 — {e}"
    except Exception as e:
        return False, f"❌ {law_info['name']}: 알 수 없는 오류 — {e}"
