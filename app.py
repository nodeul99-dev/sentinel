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
div[data-testid="collapsedControl"],
#MainMenu, footer {{ display: none !important; }}

/* 페이지 배경 */
.stApp {{
    background: #eaf2eb !important;
}}
section[data-testid="stMain"] {{
    background: #eaf2eb !important;
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
    scrollbar-color: rgba(100,116,139,0.25) transparent !important;
}}
section[data-testid="stMain"]::-webkit-scrollbar {{ width: 4px; }}
section[data-testid="stMain"]::-webkit-scrollbar-thumb {{
    background: rgba(100,116,139,0.25);
    border-radius: 4px;
}}

/* Streamlit 내부 여백 초기화 */
section[data-testid="stMain"] > div:first-child,
section[data-testid="stMain"] > div:first-child > div:first-child {{
    margin: 0 !important;
    padding: 0 !important;
}}
.block-container {{
    padding: 0 0 2rem 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
    background: transparent !important;
}}
div[data-testid="stVerticalBlock"] {{
    padding: 0 !important;
    gap: 0 !important;
}}

/* ── 메인·보조 패널 컬럼 (흰 둥근 박스) ── */
div[data-testid="stColumn"] {{
    background: #ffffff !important;
    border-radius: 9px !important;
    box-shadow: 0 1px 8px rgba(0,0,0,.07) !important;
    padding: 22px 26px !important;
}}
div[data-testid="stColumn"] div[data-testid="stColumn"] {{
    background: transparent !important;
    border-radius: 0 !important;
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
    background: #ffffff !important;
    border: 1px solid #a3e635 !important;
    border-radius: 6px !important;
    color: #14532d !important;
    font-weight: 600 !important;
    transition: background 0.15s, box-shadow 0.15s !important;
}}
div.stButton > button[kind="secondary"]:hover {{
    background: #f0f9f2 !important;
    box-shadow: 0 2px 8px rgba(163,230,53,0.2) !important;
    border-color: #84cc16 !important;
}}
.card-btn div.stButton > button[kind="secondary"] {{
    text-align: left !important;
    border: 1px solid #d1e8d4 !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    height: auto !important;
    max-height: 130px !important;
    overflow: hidden !important;
    white-space: pre-wrap !important;
    line-height: 1.7 !important;
    color: #334155 !important;
    font-size: 0.84rem !important;
    font-weight: 400 !important;
    margin-bottom: 6px !important;
}}
.card-btn div.stButton > button[kind="secondary"]:hover {{
    border-color: #a3e635 !important;
    box-shadow: 0 2px 10px rgba(163,230,53,0.15) !important;
    background: #f9fef0 !important;
}}
div.stButton > button[kind="primary"] {{
    background: #a3e635 !important;
    color: #14532d !important;
    border: none !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
}}
div.stButton > button[kind="primary"]:hover {{ background: #84cc16 !important; }}

/* ── 탭 ── */
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    border-bottom: 2px solid #84cc16 !important;
    color: #4d7c0f !important;
    font-weight: 600 !important;
}}

/* ── 체크박스 ── */
div[data-testid="stCheckbox"] input[type="checkbox"] {{
    accent-color: #84cc16 !important;
}}

/* ── 사이드바 링크 hover ── */
.sb-link {{
    color: #64748b !important;
}}
.sb-link:hover {{
    color: #a3e635 !important;
}}

/* ── 구분선 ── */
hr {{ border-color: #c8dfc9 !important; }}

/* ── 보조 패널 스크롤 ── */
.side-scroll {{
    max-height: calc(100vh - 170px);
    overflow-y: auto;
    padding-right: 4px;
}}
</style>
""", unsafe_allow_html=True)

# ── SVG 아이콘 ─────────────────────────────────────────────────────────────────
_svg_search  = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>'
_svg_finance = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
_svg_docs    = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>'
_svg_chart   = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>'
_svg_gear    = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
_svg_comm    = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
_lnk = "display:flex;align-items:center;border-radius:6px;text-decoration:none;margin:1px 0;transition:color 0.15s;"

# ── 페이지별 사이드바 메뉴 ─────────────────────────────────────────────────────
_SIDEBAR_MENUS = {
    "search": [
        ("search",  _svg_search, "규정검색",  ""),
        ("docs",    _svg_docs,   "문서관리",   "subpage=docs"),
    ],
    "finance": [
        ("finance",  _svg_chart,   "대시보드",  ""),
        ("data",     _svg_gear,    "데이터관리", "subpage=data"),
    ],
    "committee": [
        ("committee", _svg_comm, "위원회", ""),
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
    background:#0f172a;
    border-radius:9px;
    box-shadow:0 2px 12px rgba(0,0,0,.18);
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
    ("규정검색",    "search"),
    ("재무건전성비율", "finance"),
    ("위원회",     "committee"),
]

menu_pills = "".join(
    (
        f'<a href="/?page={mp}" target="_self" style="'
        f'padding:5px 16px;border-radius:20px;font-size:1.08rem;font-weight:600;'
        f'background:#a3e635;color:#14532d;border:1px solid #a3e635;'
        f'text-decoration:none;cursor:pointer;">'
        f'{html_lib.escape(ml)}</a>'
    )
    if mp == page else
    (
        f'<a href="/?page={mp}" target="_self" class="menu-pill-inactive" style="'
        f'padding:5px 16px;border-radius:20px;font-size:1.08rem;font-weight:600;'
        f'background:transparent;color:#94a3b8;border:1px solid transparent;'
        f'text-decoration:none;cursor:pointer;transition:all 0.15s;">'
        f'{html_lib.escape(ml)}</a>'
    )
    for ml, mp in _TOP_MENUS
)

st.markdown(f"""
<div style="
    background:#fff;
    border-radius:9px;
    box-shadow:0 1px 8px rgba(0,0,0,.07);
    padding:0 28px;display:flex;align-items:center;
    justify-content:space-between;height:68px;
    position:fixed;top:8px;left:8px;right:8px;z-index:999;
">
    <div style="display:flex;align-items:flex-end;gap:10px;min-width:140px;position:relative;left:-5px;">
        <div style="font-size:2.1rem;font-weight:700;color:#0f172a;text-decoration:underline;line-height:1.1;">
            sentinel.DS
        </div>
        <div style="font-size:0.72rem;color:#94a3b8;padding-bottom:1px;position:relative;top:2px;">
            DS투자증권 리스크관리팀
        </div>
    </div>
    <div style="display:flex;gap:4px;align-items:center;">{menu_pills}</div>
    <div style="min-width:140px;"></div>
</div>
""", unsafe_allow_html=True)

# ── 보조 패널 (규정검색 전용) ────────────────────────────────────────────────
def _render_side_panel():
    article = st.session_state.get("side_panel")
    keyword = st.session_state.get("_last_keyword", "")

    if article:
        c1, c2 = st.columns([5, 1])
        with c1:
            doc_name   = article["doc_name"]
            doc_cat    = article["doc_category"]
            badge_html = category_badge(doc_cat)
            st.markdown(
                f'<div style="font-size:0.78rem;color:#64748b;padding-top:6px;">'
                f'{html_lib.escape(doc_name)}&nbsp;{badge_html}</div>',
                unsafe_allow_html=True,
            )
        with c2:
            if st.button("✕", key="close_panel", type="primary"):
                del st.session_state["side_panel"]
                st.rerun()
    else:
        st.markdown(
            '<div style="font-size:1.13rem;font-weight:600;color:#14532d;'
            'padding:6px 0 0;">조문 원본</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<hr style="border:0;border-top:1px solid #e2e8f0;margin:8px 0;">',
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

elif page == "committee":
    from views import committee
    committee.render(subpage)

else:
    st.error("404 - 페이지를 찾을 수 없습니다.")
