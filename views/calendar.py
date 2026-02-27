"""
캘린더 페이지 (placeholder)
"""
import streamlit as st


_FULL_HEIGHT_CSS = """
<style>
section[data-testid="stMain"] { overflow-y: hidden !important; }
.block-container { padding-bottom: 0 !important; }
div[data-testid="stHorizontalBlock"] {
    height: calc(100vh - 92px) !important;
    align-items: stretch !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {
    height: 100% !important;
    position: static !important;
    align-self: stretch !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
    height: 100% !important;
}
</style>
"""


def render(subpage: str = None):
    st.markdown(_FULL_HEIGHT_CSS, unsafe_allow_html=True)
    col_main, col_side = st.columns([2.2, 1.1])

    with col_main:
        st.markdown(
            '<p style="font-size:1.13rem;font-weight:600;color:#1A1A1A;margin:0 0 2px;">'
            '캘린더</p>'
            '<p style="font-size:0.75rem;color:#5C5C5C;margin:0 0 20px;">'
            '리스크관리실 일정 관리 캘린더입니다.</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<hr style="border:0;border-top:1px solid #e2e8f0;margin:0 0 32px;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;color:#94a3b8;">'
            '<div style="font-size:2.5rem;margin-bottom:16px;">📅</div>'
            '<div style="font-size:0.9rem;line-height:1.8;color:#64748b;">'
            '구글 캘린더 임베딩 기능이 제공될 예정입니다.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with col_side:
        st.markdown(
            '<p style="font-size:1.13rem;font-weight:600;color:#1A1A1A;margin:0 0 2px;">'
            '일정 상세</p>'
            '<p style="font-size:0.75rem;margin:0 0 20px;">&nbsp;</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<hr style="border:0;border-top:1px solid #e2e8f0;margin:0 0 32px;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="text-align:center;padding:40px 12px;color:#94a3b8;">'
            '<div style="font-size:0.83rem;line-height:1.7;">'
            '일정을 선택하면<br>상세 내용이 표시됩니다.'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
