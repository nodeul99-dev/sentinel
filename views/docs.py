import io

import streamlit as st

from db import (
    upsert_document, insert_articles, update_article_count,
    get_all_documents, delete_document,
)
from utils.parser import parse_pdf, extract_enacted_date
from api.law_api import MANAGED_LAWS, crawl_single_law

# 업로드 가능 분류: 법령·감독규정은 크롤링으로만 등록
UPLOAD_CATEGORIES = ["모범규준", "사규"]

CATEGORY_COLORS = {
    "법령":    "#4A7C59",
    "모범규준": "#3A5F8B",
    "사규":    "#6A6A6A",
    "감독규정": "#B87333",
}


def render():
    st.markdown(
        '<p style="font-size:1.13rem;font-weight:600;color:#1A1A1A;margin:0 0 2px;">'
        '문서 관리</p>'
        '<p style="font-size:0.75rem;color:#5C5C5C;margin:0 0 20px;">'
        'PDF 업로드 또는 법제처 API를 통해 규정 문서를 등록·관리합니다.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<hr style="border:0;border-top:1px solid #e2e8f0;margin:0 0 32px;">',
        unsafe_allow_html=True,
    )

    # ── 전체 법령 업데이트 버튼 ───────────────────────────────────────────────
    col_btn, col_desc = st.columns([2, 5])
    with col_btn:
        update_all = st.button("전체 법령 업데이트", type="primary", use_container_width=True)
    with col_desc:
        st.markdown(
            '<p style="font-size:0.78rem;color:#888;padding-top:8px;">'
            '법제처 오픈API로 법령·감독규정 최신화 (.env에 LAW_API_KEY 필요)</p>',
            unsafe_allow_html=True,
        )

    if update_all:
        _run_crawler_update(MANAGED_LAWS)

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)

    tab_upload, tab_list = st.tabs(["규정 업로드", "등록된 규정"])

    # ── 업로드 섹션 (모범규준·사규 전용) ───────────────────────────────────
    with tab_upload:
        st.markdown(
            '<p style="font-size:0.85rem;color:#888;margin-bottom:4px;">'
            'PDF를 업로드하면 조문 단위로 파싱하여 저장합니다.'
            ' 원본 PDF는 파싱 즉시 삭제됩니다.</p>'
            '<p style="font-size:0.78rem;color:#a0aec0;margin-bottom:16px;">'
            '⚠ 법령·감독규정은 위의 <b>전체 법령 업데이트</b> 버튼을 사용하세요.</p>',
            unsafe_allow_html=True,
        )

        with st.form("upload_form", clear_on_submit=True):
            col_name, col_cat = st.columns([3, 2])
            with col_name:
                doc_name = st.text_input("문서명", placeholder="예: NCR관리규정")
            with col_cat:
                doc_category = st.selectbox("분류", UPLOAD_CATEGORIES)

            uploaded_file = st.file_uploader("PDF 파일", type=["pdf"])
            submitted = st.form_submit_button("업로드 및 인덱싱", type="primary")

        if submitted:
            if not doc_name.strip():
                st.error("문서명을 입력해주세요.")
            elif uploaded_file is None:
                st.error("PDF 파일을 선택해주세요.")
            else:
                with st.spinner("PDF 파싱 중... (완료 후 원본 자동 삭제)"):
                    try:
                        # 메모리에서만 처리 — 디스크 저장 없음
                        pdf_bytes = io.BytesIO(uploaded_file.read())
                        articles = parse_pdf(pdf_bytes)
                        enacted_date = extract_enacted_date(pdf_bytes)
                    except ValueError as e:
                        st.error(f"파싱 오류: {e}")
                        st.stop()

                if not articles:
                    st.warning(
                        "조문을 인식하지 못했습니다. "
                        "텍스트 레이어가 없거나 '제X조' 형식의 조문이 없는 PDF일 수 있습니다."
                    )
                else:
                    doc_id = upsert_document(
                        doc_name.strip(), doc_category, "",
                        enacted_date, source_type="pdf",
                    )
                    insert_articles(doc_id, articles)
                    update_article_count(doc_id, len(articles))
                    st.success(
                        f'"{doc_name}" 업로드 완료 — {len(articles)}개 조문 인식'
                        f'{"  (시행일: " + enacted_date + ")" if enacted_date else ""}'
                    )
                    st.rerun()

    # ── 등록 문서 목록 ────────────────────────────────────────────────────
    with tab_list:
        docs = get_all_documents()
        if not docs:
            st.markdown(
                '<p style="font-size:0.85rem;color:#999;">등록된 문서가 없습니다.</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<p style="font-size:0.8rem;color:#999;margin-bottom:12px;">'
                f'총 {len(docs)}개 문서</p>',
                unsafe_allow_html=True,
            )

            # 개별 법령 업데이트 버튼
            crawler_docs = [d for d in docs if d.get("source_type") == "crawler"]
            if crawler_docs:
                with st.expander("개별 법령 업데이트"):
                    for law in MANAGED_LAWS:
                        if st.button(
                            f"업데이트 — {law['name']}",
                            key=f"upd_{law['name']}",
                        ):
                            _run_crawler_update([law])

            # 문서 목록 테이블
            rows_html = ""
            for i, doc in enumerate(docs):
                color = CATEGORY_COLORS.get(doc["doc_category"], "#666")
                cat_badge = (
                    f'<span style="background:{color};color:#fff;'
                    f'padding:2px 8px;border-radius:3px;font-size:0.72rem;'
                    f'font-weight:500;letter-spacing:0.02em;white-space:nowrap;">'
                    f'{doc["doc_category"]}</span>'
                )

                source_type = doc.get("source_type", "pdf")
                if source_type == "crawler":
                    src_color, src_label = "#0f766e", "크롤링"
                else:
                    src_color, src_label = "#6b7280", "PDF"

                src_badge = (
                    f'<span style="background:{src_color};color:#fff;'
                    f'padding:2px 6px;border-radius:3px;font-size:0.68rem;'
                    f'font-weight:600;letter-spacing:0.03em;">'
                    f'{src_label}</span>'
                )

                enacted  = doc.get("enacted_date") or "—"
                uploaded = doc.get("uploaded_at", "")
                uploaded = uploaded[:10] if uploaded else "—"
                bg = "#fff" if i % 2 == 0 else "#fafafa"

                rows_html += (
                    f'<tr style="background:{bg};">'
                    f'<td style="padding:10px 14px;font-size:0.85rem;font-weight:600;color:#1a1a1a;">'
                    f'{doc["doc_name"]}</td>'
                    f'<td style="padding:10px 14px;text-align:center;">{cat_badge}</td>'
                    f'<td style="padding:10px 14px;text-align:center;">{src_badge}</td>'
                    f'<td style="padding:10px 14px;text-align:center;font-size:0.82rem;color:#555;">'
                    f'{doc["article_count"]}</td>'
                    f'<td style="padding:10px 14px;text-align:center;font-size:0.82rem;color:#555;">'
                    f'{enacted}</td>'
                    f'<td style="padding:10px 14px;text-align:center;font-size:0.82rem;color:#999;">'
                    f'{uploaded}</td>'
                    f'</tr>'
                )

            table_html = f"""
            <style>
                .reg-table {{
                    width: 100%;
                    border-collapse: collapse;
                    border: 1px solid #d1e8d4;
                    border-radius: 6px;
                    overflow: hidden;
                    font-family: inherit;
                }}
                .reg-table th {{
                    background: #14532d;
                    color: #fff;
                    padding: 10px 14px;
                    font-size: 0.78rem;
                    font-weight: 600;
                    letter-spacing: 0.04em;
                    text-align: center;
                }}
                .reg-table th:first-child {{ text-align: left; }}
                .reg-table td {{ border-top: 1px solid #d1e8d4; }}
                .reg-table tr:hover td {{ background: #f0f9f2 !important; }}
            </style>
            <table class="reg-table">
                <thead>
                    <tr>
                        <th style="width:34%;">문서명</th>
                        <th style="width:12%;">분류</th>
                        <th style="width:10%;">소스</th>
                        <th style="width:8%;">조문 수</th>
                        <th style="width:16%;">시행일</th>
                        <th style="width:16%;">업데이트일</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            """
            st.markdown(table_html, unsafe_allow_html=True)

            # 삭제 섹션
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            with st.expander("문서 삭제"):
                doc_options = {
                    f"{d['doc_name']}  [{d['doc_category']}]": d["id"] for d in docs
                }
                selected = st.selectbox(
                    "삭제할 문서", list(doc_options.keys()), label_visibility="collapsed"
                )
                if st.button("삭제", type="primary"):
                    st.session_state["confirm_del_id"]   = doc_options[selected]
                    st.session_state["confirm_del_name"] = selected

            if "confirm_del_id" in st.session_state:
                st.warning(f'"{st.session_state["confirm_del_name"]}" 를 삭제하시겠습니까?')
                c1, c2, _ = st.columns([1, 1, 6])
                with c1:
                    if st.button("확인", type="primary"):
                        delete_document(st.session_state["confirm_del_id"])
                        st.session_state.pop("confirm_del_id", None)
                        st.session_state.pop("confirm_del_name", None)
                        st.rerun()
                with c2:
                    if st.button("취소", type="primary"):
                        st.session_state.pop("confirm_del_id", None)
                        st.session_state.pop("confirm_del_name", None)
                        st.rerun()


def _run_crawler_update(laws: list[dict]):
    """법령 목록을 순서대로 크롤링하여 DB에 저장."""
    progress = st.progress(0, text="업데이트 준비 중...")
    results = []
    for i, law in enumerate(laws):
        progress.progress(i / len(laws), text=f"수신 중: {law['name']}")
        success, msg = crawl_single_law(law)
        results.append((success, msg))
    progress.progress(1.0, text="완료")
    for success, msg in results:
        if success:
            st.success(msg)
        else:
            st.error(msg)
    st.rerun()
