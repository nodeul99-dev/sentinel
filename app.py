"""
Sentinel.DS 리스크 포털 - 메인 앱
"""
import sys
import os
import html as html_lib

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

import db
from utils.search import highlight_full_text, category_badge

st.set_page_config(
    page_title="Sentinel.DS | DS투자증권 리스크 포털",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── DB 초기화 ─────────────────────────────────────────────────────────────────
db.init_db()
db.init_fss_tables()
db.init_pnl_tables()

SB_W       = "70px"
SB_TOTAL_W = "86px"  # left:8px + width:70px + gap:8px

# ── URL 파라미터 ──────────────────────────────────────────────────────────────
page    = st.query_params.get("page", "search")
subpage = st.query_params.get("subpage", None)

# ── 전역 CSS ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* 기본 UI 숨김 */
header[data-testid="stHeader"],
div[data-testid="stDecoration"],
div[data-testid="collapsedControl"],
#MainMenu, footer {{ display: none !important; }}

/* 페이지 배경 */
.stApp {{
    background: #F7F5F2 !important;
}}
section[data-testid="stMain"] {{
    background: #F7F5F2 !important;
    position: fixed !important;
    top: 84px !important;
    left: {SB_TOTAL_W} !important;
    right: 8px !important;
    bottom: 0 !important;
    overflow-y: auto !important;
    width: auto !important;
    margin: 0 !important;
    padding: 0 !important;
    scrollbar-width: thin !important;
    scrollbar-color: rgba(26,26,26,0.15) transparent !important;
}}
section[data-testid="stMain"]::-webkit-scrollbar {{ width: 4px; }}
section[data-testid="stMain"]::-webkit-scrollbar-thumb {{
    background: rgba(26,26,26,0.15);
    border-radius: 4px;
}}

/* Streamlit 내부 여백 초기화 + 스크롤 보장 */
section[data-testid="stMain"] > div,
section[data-testid="stMain"] > div > div {{
    margin: 0 !important;
    padding: 0 !important;
    height: auto !important;
    overflow: visible !important;
}}
div[data-testid="stMainBlockContainer"] {{
    height: auto !important;
    overflow: visible !important;
    padding: 0 !important;
}}
.block-container {{
    padding: 0 0 4rem 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
    background: transparent !important;
    height: auto !important;
    overflow: visible !important;
}}
div[data-testid="stVerticalBlock"] {{
    padding: 0 !important;
    gap: 0 !important;
    height: auto !important;
}}

/* ── 메인·보조 패널 컬럼 (흰 박스) ── */
div[data-testid="stColumn"] {{
    background: #FFFFFF !important;
    border-radius: 9px !important;
    border: 1px solid #E8E4DE !important;
    box-shadow: none !important;
    padding: 22px 26px !important;
}}
div[data-testid="stColumn"] div[data-testid="stColumn"] {{
    background: transparent !important;
    border-radius: 0 !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 4px !important;
}}

/* ── 패널 간격 ── */
div[data-testid="stColumns"],
div[data-testid="stHorizontalBlock"] {{
    gap: 10px !important;
    align-items: flex-start !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
}}

/* ── 보조 패널 sticky ── */
div[data-testid="stColumns"] > div[data-testid="stColumn"]:last-child,
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {{
    position: sticky !important;
    top: 0 !important;
    align-self: flex-start !important;
}}

/* ── 버튼 스타일 ── */
div.stButton > button[kind="secondary"] {{
    background: #FFFFFF !important;
    border: 1px solid #1A1A1A !important;
    border-radius: 6px !important;
    color: #1A1A1A !important;
    font-weight: 600 !important;
    transition: background 0.15s, box-shadow 0.15s !important;
}}
div.stButton > button[kind="secondary"]:hover {{
    background: #F7F5F2 !important;
    box-shadow: 0 2px 8px rgba(26,26,26,0.12) !important;
    border-color: #333333 !important;
}}
.card-btn div.stButton > button[kind="secondary"] {{
    text-align: left !important;
    border: 1px solid #E8E4DE !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    height: auto !important;
    max-height: 130px !important;
    overflow: hidden !important;
    white-space: pre-wrap !important;
    line-height: 1.7 !important;
    color: #5A5A5A !important;
    font-size: 0.84rem !important;
    font-weight: 400 !important;
    margin-bottom: 6px !important;
}}
.card-btn div.stButton > button[kind="secondary"]:hover {{
    border-color: #C8A96E !important;
    box-shadow: 0 2px 10px rgba(200,169,110,0.2) !important;
    background: #FAF8F5 !important;
}}
div.stButton > button[kind="primary"] {{
    background: #1A1A1A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
}}
div.stButton > button[kind="primary"]:hover {{ background: #333333 !important; }}

/* ── 탭 ── */
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    border-bottom: 2px solid #C8A96E !important;
    color: #1A1A1A !important;
    font-weight: 600 !important;
}}

/* ── 체크박스 ── */
div[data-testid="stCheckbox"] input[type="checkbox"] {{
    accent-color: #C8A96E !important;
}}

/* ── 사이드바 링크 hover ── */
.sb-link {{
    color: #9A9690 !important;
}}
.sb-link:hover {{
    color: #C8A96E !important;
    filter: brightness(1.2) drop-shadow(0 0 6px rgba(200,169,110,0.7)) !important;
}}

/* ── 상단바 비활성 메뉴 hover ── */
.menu-pill-inactive:hover {{
    background: rgba(200,169,110,0.12) !important;
    border-color: #C8A96E !important;
    color: #1A1A1A !important;
}}

/* ── 구분선 ── */
hr {{ border-color: #E8E4DE !important; }}

/* ── 보조 패널 스크롤 ── */
.side-scroll {{
    max-height: calc(100vh - 170px);
    overflow-y: auto;
    padding-right: 4px;
}}
</style>
""", unsafe_allow_html=True)

# ── SVG 아이콘 ─────────────────────────────────────────────────────────────────
_svg_search   = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>'
_svg_finance  = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
_svg_docs     = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>'
_svg_chart    = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>'
_svg_gear     = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
_svg_comm     = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
_svg_risk     = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
_svg_pnl      = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>'
_svg_stress   = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
_svg_calendar = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
_lnk = "display:flex;align-items:center;border-radius:6px;text-decoration:none;margin:1px 0;transition:color 0.15s;"

# ── 페이지별 사이드바 메뉴 ─────────────────────────────────────────────────────
_SIDEBAR_MENUS = {
    "risk": [
        ("risk", _svg_risk, "리스크현황", ""),
    ],
    "pnl": [
        ("pnl",   _svg_pnl,  "손익집계", ""),
        ("input", _svg_gear, "입력관리", "subpage=input"),
    ],
    "stress": [
        ("stress", _svg_stress, "스트레스테스트", ""),
    ],
    "committee": [
        ("committee", _svg_comm, "위원회", ""),
    ],
    "calendar": [
        ("calendar", _svg_calendar, "캘린더", ""),
    ],
    "finance": [
        ("finance",  _svg_chart,   "대시보드",  ""),
        ("data",     _svg_gear,    "데이터관리", "subpage=data"),
    ],
    "search": [
        ("search",  _svg_search, "규정검색",  ""),
        ("docs",    _svg_docs,   "문서관리",   "subpage=docs"),
    ],
}

menus = _SIDEBAR_MENUS.get(page, [])
_nav_html = ""
for _sp, _ni, _nl, _qp in menus:
    _href = f"/?page={page}&{_qp}" if _qp else f"/?page={page}"
    _nav_html += (
        f'<a href="{_href}" target="_self" class="sb-link" style="{_lnk}'
        f'justify-content:center;padding:20px 0;">'
        f'<span style="display:flex;">{_ni}</span>'
        f'</a>'
    )

# ── 사이드바 ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="
    position:fixed; left:8px; top:84px;
    width:{SB_W}; height:calc(100vh - 92px);
    background:#5a4d42;
    border-radius:9px;
    box-shadow:none;
    overflow:hidden;
    z-index:100;
    box-sizing:border-box;
    padding:0 8px;
">
  <div style="padding-top:8px;">
    <nav>{_nav_html}</nav>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 상단바 ────────────────────────────────────────────────────────────────────
_TOP_MENUS = [
    ("리스크현황",       "risk"),
    ("손익집계",         "pnl"),
    ("시뮬레이션",   "stress"),
    ("위원회",       "committee"),
    ("캘린더",           "calendar"),
    ("재무건전성비율",   "finance"),
    ("규정검색",         "search"),
]

menu_pills = "".join(
    (
        f'<a href="/?page={mp}" target="_self" style="'
        f'padding:5px 6px;border-radius:20px;font-size:0.92rem;font-weight:600;'
        f'background:#C8A96E;color:#FFFFFF;border:1px solid #C8A96E;'
        f'text-decoration:none;cursor:pointer;">'
        f'{html_lib.escape(ml)}</a>'
    )
    if mp == page else
    (
        f'<a href="/?page={mp}" target="_self" class="menu-pill-inactive" style="'
        f'padding:5px 6px;border-radius:20px;font-size:0.92rem;font-weight:600;'
        f'background:transparent;color:#5A5A5A;border:1px solid transparent;'
        f'text-decoration:none;cursor:pointer;transition:all 0.15s;">'
        f'{html_lib.escape(ml)}</a>'
    )
    for ml, mp in _TOP_MENUS
)

st.markdown(f"""
<div style="
    background:#FFFFFF;
    border-radius:9px;
    border-bottom:2px solid #1A1A1A;
    padding:0 28px;display:flex;align-items:center;
    justify-content:flex-start;gap:32px;height:68px;
    position:fixed;top:8px;left:8px;right:8px;z-index:999;
">
    <div style="display:flex;align-items:flex-end;gap:10px;flex-shrink:0;position:relative;left:-5px;">
        <div style="position:relative;display:inline-block;">
            <div style="font-size:2.31rem;font-weight:700;color:#1A1A1A;text-decoration:underline;line-height:1.1;">
                Project Sentinel
            </div>
            <span style="
                position:absolute;top:-2px;right:-41px;
                background:#F5C518;color:#1A1A1A;
                font-size:0.58rem;font-weight:700;
                padding:2px 5px;border-radius:4px;
                letter-spacing:0.06em;line-height:1.4;
            ">ALPHA</span>
        </div>
        <div style="font-size:0.72rem;color:#9A9690;padding-bottom:1px;position:relative;top:2px;">
            DS투자증권 리스크관리팀
        </div>
    </div>
    <div style="display:flex;gap:2px;align-items:center;position:relative;top:3px;">{menu_pills}</div>
</div>
""", unsafe_allow_html=True)

# ── 보조 패널 (규정검색 전용) ────────────────────────────────────────────────
def _render_side_panel():
    article = st.session_state.get("side_panel")
    keyword = st.session_state.get("_last_keyword", "")

    st.markdown(
        '<p style="font-size:1.13rem;font-weight:600;color:#1A1A1A;margin:0 0 2px;">조문 원본</p>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([5, 1])
    with c1:
        if article:
            doc_name   = article["doc_name"]
            doc_cat    = article["doc_category"]
            badge_html = category_badge(doc_cat)
            st.markdown(
                f'<p style="font-size:0.75rem;color:#5C5C5C;margin:0 0 20px;">'
                f'{html_lib.escape(doc_name)}&nbsp;{badge_html}</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p style="font-size:0.75rem;margin:0 0 20px;">&nbsp;</p>',
                unsafe_allow_html=True,
            )
    with c2:
        if article:
            if st.button("✕", key="close_panel", type="primary"):
                del st.session_state["side_panel"]
                st.rerun()

    st.markdown(
        '<hr style="border:0;border-top:1px solid #e2e8f0;margin:0 0 32px;">',
        unsafe_allow_html=True,
    )

    if article is None:
        st.markdown(
            '<div style="text-align:center;padding:48px 20px;color:#94a3b8;">'
            '<div style="font-size:2.2rem;margin-bottom:14px;">📄</div>'
            '<div style="font-size:0.83rem;line-height:1.7;">'
            '검색 결과 카드의<br>'
            '<b style="color:#64748b;">전문 보기</b>를 클릭하면<br>'
            '조문 원본이 여기에 표시됩니다.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    art_num   = article.get("article_number") or ""
    art_title = article.get("article_title") or ""
    art_text  = article.get("article_text", "")
    enacted   = article.get("enacted_date") or ""
    title_str = f" ({art_title})" if art_title else ""

    st.markdown(
        f'<div style="font-size:1rem;font-weight:700;color:#0f172a;margin-bottom:4px;">'
        f'{html_lib.escape(art_num)}{html_lib.escape(title_str)}</div>'
        + (f'<div style="font-size:0.73rem;color:#94a3b8;margin-bottom:12px;">'
           f'시행 {html_lib.escape(enacted)}</div>' if enacted else ''),
        unsafe_allow_html=True,
    )

    full_html = highlight_full_text(art_text, keyword)
    st.markdown(
        f'<div class="side-scroll" style="'
        f'background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;'
        f'padding:16px 18px;font-size:0.84rem;color:#334155;'
        f'line-height:1.85;white-space:pre-wrap;word-break:keep-all;">'
        f'{full_html}</div>',
        unsafe_allow_html=True,
    )


# ── 라우팅 ───────────────────────────────────────────────────────────────────
if page == "search":
    col_main, col_side = st.columns([2.2, 1.1])
    with col_main:
        if subpage == "docs":
            from views import docs
            docs.render()
        else:
            from views import search_page
            search_page.render()
    with col_side:
        _render_side_panel()

elif page == "finance":
    from views import finance
    finance.render(subpage)

elif page == "risk":
    from views import risk
    risk.render(subpage)

elif page == "pnl":
    from views import pnl
    pnl.render(subpage)

elif page == "stress":
    from views import stress
    stress.render(subpage)

elif page == "committee":
    from views import committee
    committee.render(subpage)

elif page == "calendar":
    from views import calendar
    calendar.render(subpage)

else:
    st.error("404 - 페이지를 찾을 수 없습니다.")
