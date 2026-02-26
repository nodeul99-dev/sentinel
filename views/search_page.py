import html
import urllib.parse

import streamlit as st

from utils.search import run_search, highlight_full_text, highlight_snippet, normalize_article_text, category_badge, CATEGORIES


def render():
    # ── 히스토리 클릭 → 검색창 자동 입력 (URL 파라미터 방식) ────────────────
    if "hist_kw" in st.query_params:
        kw = st.query_params["hist_kw"]
        st.session_state["search_keyword"] = kw
        del st.query_params["hist_kw"]

    st.markdown(
        '<p style="font-size:1.13rem;font-weight:600;color:#14532d;margin:0 0 2px;">'
        '규정 검색</p>'
        '<p style="font-size:0.75rem;color:#999;margin:0 0 12px;">'
        '검색어를 입력하면 해당 단어가 포함된 조문을 즉시 확인할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )

    # ── 검색창 ──────────────────────────────────────────────────────────────
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        keyword = st.text_input(
            "검색어",
            label_visibility="collapsed",
            placeholder="검색어 입력 (예: 순자본비율, 위험액, VaR)",
            key="search_keyword",
        )
    with col_btn:
        search_clicked = st.button("검색", type="primary", use_container_width=True)

    # ── 검색 히스토리 ────────────────────────────────────────────────────────
    history = st.session_state.get("_search_history", [])
    if history:
        links = " <span style='color:#ddd;margin:0 2px;'>·</span> ".join(
            f'<a href="/?page=search&hist_kw={urllib.parse.quote(kw)}" target="_self"'
            f' style="color:#16a34a;font-size:0.78rem;text-decoration:none;'
            f'border-bottom:1px dotted #4ade80;">{html.escape(kw)}</a>'
            for kw in history
        )
        st.markdown(
            f'<div style="margin:4px 0 8px;">'
            f'<span style="font-size:0.72rem;color:#4ade80;font-weight:600;'
            f'margin-right:8px;letter-spacing:0.03em;">최근</span>{links}</div>',
            unsafe_allow_html=True,
        )

    # ── 분류 필터 ────────────────────────────────────────────────────────────
    filter_cols = st.columns([0.6] + [1] * len(CATEGORIES))
    selected_categories = []
    with filter_cols[0]:
        st.markdown(
            '<div style="padding-top:7px;font-size:0.72rem;color:#bbb;'
            'font-weight:600;letter-spacing:0.05em;">필터</div>',
            unsafe_allow_html=True,
        )
    for i, cat in enumerate(CATEGORIES):
        with filter_cols[i + 1]:
            if st.checkbox(cat, value=True, key=f"filter_{cat}"):
                selected_categories.append(cat)

    st.divider()

    # ── 검색 실행 ────────────────────────────────────────────────────────────
    if keyword and (search_clicked or st.session_state.get("_last_keyword") != keyword):
        # 히스토리 업데이트 (중복 제거 후 맨 앞 삽입, 최대 6개)
        hist = st.session_state.get("_search_history", [])
        if keyword in hist:
            hist.remove(keyword)
        hist.insert(0, keyword)
        st.session_state["_search_history"] = hist[:6]

        st.session_state["_last_keyword"] = keyword
        st.session_state["_results"] = run_search(keyword, selected_categories)
        st.session_state["_page"] = 0
    elif not keyword:
        st.session_state.pop("_results", None)
        st.session_state.pop("_last_keyword", None)
        st.session_state["_page"] = 0

    results = st.session_state.get("_results")

    if results is None:
        st.markdown(
            '<p style="color:#999;font-size:0.88rem;">검색어를 입력하고 검색 버튼을 누르세요.</p>',
            unsafe_allow_html=True,
        )
        return

    if not results:
        st.markdown(
            f'<p style="color:#666;font-size:0.88rem;">'
            f'<b>"{keyword}"</b> 에 해당하는 조문을 찾을 수 없습니다.</p>',
            unsafe_allow_html=True,
        )
        return

    # ── 페이지당 결과 수 선택 ────────────────────────────────────────────────
    col_info, col_per_page = st.columns([4, 1])
    with col_info:
        st.markdown(
            f'<span style="font-size:0.88rem;color:#555;">검색 결과 <b>{len(results)}건</b>'
            f' &mdash; &ldquo;{html.escape(keyword)}&rdquo;</span>',
            unsafe_allow_html=True,
        )
    with col_per_page:
        per_page = st.selectbox(
            "페이지당 결과",
            options=[10, 30, 50, 100],
            index=0,
            key="per_page",
            label_visibility="collapsed",
        )

    # ── 페이지네이션 계산 ────────────────────────────────────────────────────
    total        = len(results)
    total_pages  = max(1, (total + per_page - 1) // per_page)
    current_page = min(st.session_state.get("_page", 0), total_pages - 1)

    start        = current_page * per_page
    end          = min(start + per_page, total)
    page_results = results[start:end]

    st.markdown("")
    for row in page_results:
        _render_article_card(row, keyword)

    # ── 페이지 이동 버튼 ─────────────────────────────────────────────────────
    if total_pages > 1:
        st.divider()
        pcol1, pcol2, pcol3 = st.columns([1, 3, 1])
        with pcol1:
            if st.button("← 이전", type="primary", disabled=(current_page == 0), use_container_width=True):
                st.session_state["_page"] = current_page - 1
                st.rerun()
        with pcol2:
            st.markdown(
                f'<div style="text-align:center;padding-top:6px;font-size:0.85rem;color:#888;">'
                f"{current_page + 1} / {total_pages} 페이지 "
                f"({start + 1}–{end} / {total}건)"
                f"</div>",
                unsafe_allow_html=True,
            )
        with pcol3:
            if st.button("다음 →", type="primary", disabled=(current_page >= total_pages - 1), use_container_width=True):
                st.session_state["_page"] = current_page + 1
                st.rerun()


def _render_article_card(row: dict, keyword: str):
    article_number = row["article_number"] or ""
    article_title  = row["article_title"] or ""
    doc_name       = row["doc_name"]
    doc_category   = row["doc_category"]
    article_text   = row["article_text"]
    source_type    = row.get("source_type", "pdf")
    enacted_date   = row.get("enacted_date") or ""

    title_str = f"({article_title})" if article_title else ""
    src_label = "크롤링" if source_type == "crawler" else "PDF"
    date_part = f"  ·  시행 {enacted_date}" if enacted_date else ""

    # 정규화 + 3줄 분량 스니펫
    text = normalize_article_text(article_text).replace("\n", " ")
    if keyword:
        idx = text.lower().find(keyword.lower())
        if idx >= 0:
            s = max(0, idx - 30)
            e = min(len(text), idx + len(keyword) + 100)
            snippet = ("…" if s > 0 else "") + text[s:e] + ("…" if e < len(text) else "")
        else:
            snippet = text[:130] + ("…" if len(text) > 130 else "")
    else:
        snippet = text[:130] + ("…" if len(text) > 130 else "")

    active    = st.session_state.get("side_panel")
    is_active = active is not None and active.get("id") == row.get("id")
    prefix    = "▶ " if is_active else ""

    label = (
        f"{prefix}{doc_name}  [{doc_category} · {src_label}]{date_part}\n"
        f"**{article_number}{'  ' + title_str if title_str else ''}**\n"
        f"{snippet}"
    )

    st.markdown('<div class="card-btn">', unsafe_allow_html=True)
    if st.button(label, key=f"card_{row['id']}", use_container_width=True):
        st.session_state["side_panel"] = row
    st.markdown('</div>', unsafe_allow_html=True)
