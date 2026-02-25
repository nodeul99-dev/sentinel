"""
위원회 페이지 (placeholder)
"""
import streamlit as st


def render(subpage: str = None):
    st.markdown(
        '<p style="font-size:0.85rem;font-weight:600;color:#14532d;margin:0 0 2px;">'
        '위원회</p>'
        '<p style="font-size:0.75rem;color:#999;margin:0 0 24px;">'
        '위원회 관련 기능은 향후 구현 예정입니다.</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="text-align:center;padding:60px 20px;color:#94a3b8;">'
        '<div style="font-size:2.5rem;margin-bottom:16px;">📋</div>'
        '<div style="font-size:0.9rem;line-height:1.8;color:#64748b;">'
        '위원회 기능은 현재 준비 중입니다.<br>'
        '빠른 시일 내에 제공될 예정입니다.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
