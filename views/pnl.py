"""
손익집계 페이지
"""
from datetime import date, timedelta

import streamlit as st
import plotly.graph_objects as go

import db

# ── 조직 구조 ─────────────────────────────────────────────────────────────────
# (division, [sub-departments])  하위 없으면 빈 리스트
DIVISIONS_STRUCTURE = [
    ("S&T",         ["에쿼티마켓", "자본시장", "FI금융", "채권금융"]),
    ("주식파생운용", ["주식운용", "시장조성", "파생운용"]),
    ("글로벌마켓",   ["글로벌대체", "IB", "프로젝트금융"]),
    ("대체투자",     ["부동산금융", "개발금융", "자산관리"]),
    ("헤지펀드",     []),
    ("기타",         []),
    ("본사공통",     []),
]

# 전체 입력 단위: (division, department) — 하위 없는 부문은 division == department
ALL_UNITS = []
for _div, _depts in DIVISIONS_STRUCTURE:
    if _depts:
        for _dept in _depts:
            ALL_UNITS.append((_div, _dept))
    else:
        ALL_UNITS.append((_div, _div))


# ── 메인 render ───────────────────────────────────────────────────────────────

def render(subpage: str = None):
    if subpage == "input":
        _render_input_page()
    else:
        _render_dashboard()


# ── 대시보드 ──────────────────────────────────────────────────────────────────

def _render_pnl_aggrid(
    d_data: dict, m_data: dict, q_data: dict, y_data: dict,
    d_lbl: str, m_lbl: str, q_lbl: str, y_lbl: str,
):
    """AgGrid Alpine 테마 손익 테이블 (행 클릭 → session_state 업데이트)"""
    import pandas as pd
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

    rows = []
    gd = gm = gq = gy = 0.0

    for div, depts in DIVISIONS_STRUCTURE:
        if depts:
            dt = sum(d_data.get((div, d), 0) or 0 for d in depts)
            mt = sum(m_data.get((div, d), 0) or 0 for d in depts)
            qt = sum(q_data.get((div, d), 0) or 0 for d in depts)
            yt = sum(y_data.get((div, d), 0) or 0 for d in depts)
            gd += dt; gm += mt; gq += qt; gy += yt
            rows.append({
                "부문_본부": div,
                "전일": dt, "월간": mt, "분기": qt, "연간": yt,
                "_type": "div_sub", "_div": div, "_dept": "",
            })
            for dept in depts:
                rows.append({
                    "부문_본부": f"└ {dept}",
                    "전일": d_data.get((div, dept)),
                    "월간": m_data.get((div, dept)),
                    "분기": q_data.get((div, dept)),
                    "연간": y_data.get((div, dept)),
                    "_type": "dept", "_div": div, "_dept": dept,
                })
        else:
            dv = d_data.get((div, div))
            mv = m_data.get((div, div))
            qv = q_data.get((div, div))
            yv = y_data.get((div, div))
            gd += dv or 0; gm += mv or 0; gq += qv or 0; gy += yv or 0
            rows.append({
                "부문_본부": div,
                "전일": dv, "월간": mv, "분기": qv, "연간": yv,
                "_type": "nodept", "_div": div, "_dept": div,
            })

    rows.append({
        "부문_본부": "전체 합계",
        "전일": gd, "월간": gm, "분기": gq, "연간": gy,
        "_type": "total", "_div": "__all__", "_dept": "",
    })

    df = pd.DataFrame(rows)

    pnl_fmt = JsCode("""
    function(p) {
        if (p.value == null || !isFinite(p.value)) return '\u2014';
        var s = p.value >= 0 ? '+' : '';
        return s + Math.round(p.value).toLocaleString('ko-KR');
    }
    """)

    pnl_style = JsCode("""
    function(p) {
        if (!p.data) return null;
        if (p.value == null || !isFinite(p.value))
            return {color: '#9A9690', textAlign: 'right', fontWeight: '600'};
        var isTotal = p.data._type === 'total';
        var color = isTotal
            ? (p.value >= 0 ? '#F7F5F2' : '#fca5a5')
            : (p.value >= 0 ? '#1A1A1A' : '#b91c1c');
        return {color: color, textAlign: 'right', fontWeight: '600'};
    }
    """)

    name_style = JsCode("""
    function(p) {
        if (!p.data) return null;
        var t = p.data._type;
        if (t === 'dept')  return {paddingLeft: '24px', color: '#5A5A5A'};
        if (t === 'total') return {color: '#F7F5F2', fontWeight: '700'};
        return {color: '#1A1A1A'};
    }
    """)

    row_style = JsCode("""
    function(params) {
        if (!params.data) return null;
        var t = params.data._type;
        if (t === 'total')   return {background: '#2D2926'};
        if (t === 'div_sub') return {background: '#F7F5F2', fontWeight: '700'};
        if (t === 'nodept')  return {background: '#F7F5F2', fontWeight: '600'};
        return null;
    }
    """)

    on_grid_size_changed = JsCode("function(params) { params.api.sizeColumnsToFit(); }")

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_default_column(sortable=False, resizable=False, suppressMovable=True)
    gb.configure_column("부문_본부", flex=2, minWidth=140,
                        headerName="부문 / 본부  (백만원)", cellStyle=name_style)
    gb.configure_column("전일", flex=1, minWidth=90,
                        headerName=f"전일 손익 ({d_lbl})",
                        valueFormatter=pnl_fmt, cellStyle=pnl_style, type=["numericColumn"])
    gb.configure_column("월간", flex=1, minWidth=90,
                        headerName=f"월간 ({m_lbl})",
                        valueFormatter=pnl_fmt, cellStyle=pnl_style, type=["numericColumn"])
    gb.configure_column("분기", flex=1, minWidth=90,
                        headerName=f"분기 ({q_lbl})",
                        valueFormatter=pnl_fmt, cellStyle=pnl_style, type=["numericColumn"])
    gb.configure_column("연간", flex=1, minWidth=90,
                        headerName=f"연간 ({y_lbl})",
                        valueFormatter=pnl_fmt, cellStyle=pnl_style, type=["numericColumn"])
    gb.configure_column("_type", hide=True)
    gb.configure_column("_div",  hide=True)
    gb.configure_column("_dept", hide=True)
    gb.configure_grid_options(
        getRowStyle=row_style,
        rowHeight=34,
        headerHeight=40,
        onGridSizeChanged=on_grid_size_changed,
    )

    grid_response = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=40 + len(rows) * 34 + 16,
        allow_unsafe_jscode=True,
        theme="alpine",
        fit_columns_on_grid_load=True,
        key=f"pnl_grid_{d_lbl}_{m_lbl}_{q_lbl}_{y_lbl}",
    )

    sel = grid_response.selected_rows
    if sel is not None and len(sel) > 0:
        row = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
        t      = row["_type"]
        div_v  = row["_div"]
        dept_v = row["_dept"]
        if t == "total":
            entity_key = ("__all__", None)
        elif t == "div_sub":
            entity_key = (div_v, None)
        elif t == "dept":
            entity_key = (div_v, dept_v)
        else:  # nodept
            entity_key = (div_v, div_v)
        st.session_state["_pnl_entity_key"] = entity_key


def _render_dashboard():
    today      = date.today()
    yesterday  = today - timedelta(days=1)
    latest_str = db.get_pnl_latest_date()
    latest_date = date.fromisoformat(latest_str) if latest_str else yesterday

    st.markdown(
        '<style>'
        '[data-testid="stDateInput"]'
        '{display:flex !important;justify-content:flex-end !important;}'
        '[data-testid="stDateInput"] > div:last-child'
        '{width:auto !important;min-width:8rem !important;}'
        '[data-testid="stDateInput"] input'
        '{text-align:right !important;}'
        '</style>',
        unsafe_allow_html=True,
    )

    col_main, col_side = st.columns([2.2, 1.1])

    with col_main:
        c_title, c_date = st.columns([3, 1])
        with c_title:
            st.markdown(
                '<p style="font-size:1.13rem;font-weight:600;color:#1A1A1A;margin:0 0 2px;">'
                '손익집계</p>'
                '<p style="font-size:0.75rem;color:#5C5C5C;margin:0 0 4px;">'
                '프런트 부서별 손익 집계 대시보드 &nbsp;·&nbsp; 단위: 백만원</p>',
                unsafe_allow_html=True,
            )
        with c_date:
            sel_date = st.date_input(
                "기준일", value=latest_date, max_value=today,
                key="pnl_d", label_visibility="collapsed",
            )

        st.markdown(
            '<hr style="border:0;border-top:1px solid #e2e8f0;margin:6px 0 20px;">',
            unsafe_allow_html=True,
        )

        d_str = str(sel_date)
        d_lbl = f"{sel_date.month}.{sel_date.day:02d}"

        m_start = str(date(sel_date.year, sel_date.month, 1))
        m_lbl   = f"{sel_date.month}월"

        q_num   = (sel_date.month - 1) // 3 + 1
        q_start = str(date(sel_date.year, (q_num - 1) * 3 + 1, 1))
        q_lbl   = f"{q_num}Q"

        y_start = str(date(sel_date.year, 1, 1))
        y_lbl   = str(sel_date.year)

        d_data = db.get_pnl_entries_by_date(d_str)
        m_data = db.get_pnl_entries_sum(m_start, d_str)
        q_data = db.get_pnl_entries_sum(q_start, d_str)
        y_data = db.get_pnl_entries_sum(y_start, d_str)

        _render_pnl_aggrid(d_data, m_data, q_data, y_data, d_lbl, m_lbl, q_lbl, y_lbl)

        # 차트 기간 선택 (entity는 테이블 행 클릭으로 결정)
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        chart_period = st.selectbox(
            "차트 기간", ["월간", "분기", "연간"],
            key="pnl_chart_period", label_visibility="collapsed",
        )

        chart_ranges = {
            "월간": (m_start, d_str, m_lbl, m_data),
            "분기": (q_start, d_str, q_lbl, q_data),
            "연간": (y_start, d_str, y_lbl, y_data),
        }
        chart_start, chart_end, chart_period_disp, chart_pnl_data = chart_ranges[chart_period]

        entity_key = st.session_state.get("_pnl_entity_key", ("__all__", None))
        div_key, dept_key = entity_key
        if div_key == "__all__":
            sel_entity = "전체 부문"
        elif dept_key is None:
            sel_entity = div_key
        elif dept_key == div_key:
            sel_entity = div_key
        else:
            sel_entity = dept_key

        st.session_state["_pnl_chart"] = {
            "entity_key":  entity_key,
            "pnl_data":    chart_pnl_data,
            "chart_start": chart_start,
            "chart_end":   chart_end,
            "period_disp": chart_period_disp,
            "sel_entity":  sel_entity,
        }

    with col_side:
        _render_side_chart()


def _render_side_chart():
    info = st.session_state.get("_pnl_chart", {})
    entity_key  = info.get("entity_key",  ("__all__", None))
    pnl_data    = info.get("pnl_data",    {})
    chart_start = info.get("chart_start", "")
    chart_end   = info.get("chart_end",   "")
    period_disp = info.get("period_disp", "")
    sel_entity  = info.get("sel_entity",  "전체 부문")

    div_key, dept_key = entity_key if entity_key else ("__all__", None)

    st.markdown(
        '<p style="font-size:1.13rem;font-weight:600;color:#1A1A1A;margin:0 0 2px;">'
        '손익 차트</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:0.75rem;color:#5C5C5C;margin:0 0 20px;">'
        f'{period_disp or "&nbsp;"}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<hr style="border:0;border-top:1px solid #e2e8f0;margin:0 0 20px;">',
        unsafe_allow_html=True,
    )

    if div_key == "__all__":
        # 전체 부문 가로 막대 차트
        div_labels, div_values = [], []
        for div, depts in DIVISIONS_STRUCTURE:
            keys  = [(div, d) for d in depts] if depts else [(div, div)]
            total = sum(pnl_data.get(k, 0) or 0 for k in keys)
            div_labels.append(div)
            div_values.append(total)

        colors = ["#15803d" if v >= 0 else "#b91c1c" for v in div_values]
        texts  = [f"{'+'if v>0 else ''}{v:,.0f}" for v in div_values]

        fig = go.Figure(go.Bar(
            x=div_values, y=div_labels, orientation="h",
            marker_color=colors,
            text=texts, textposition="outside",
            textfont=dict(size=10),
        ))
        fig.update_layout(
            height=310,
            margin=dict(l=0, r=60, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(showgrid=False, showticklabels=False,
                       zeroline=True, zerolinecolor="#E8E4DE"),
            yaxis=dict(showgrid=False),
            font=dict(size=11, color="#1A1A1A"),
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})
    else:
        # 특정 부문/본부 일별 추이 차트
        if dept_key is None:
            trend = db.get_pnl_division_trend(div_key, chart_start, chart_end)
        else:
            trend = db.get_pnl_trend(div_key, dept_key, chart_start, chart_end)

        if not trend:
            st.markdown(
                '<div style="text-align:center;padding:60px 20px;color:#94a3b8;">'
                '<div style="font-size:0.83rem;line-height:1.7;">'
                f'<b>{sel_entity}</b><br>해당 기간에 데이터가 없습니다.'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            dates  = [r["trade_date"] for r in trend]
            values = [r["pnl_daily"] for r in trend]
            colors = ["#15803d" if v >= 0 else "#b91c1c" for v in values]
            texts  = [f"{'+'if v>0 else ''}{v:,.0f}" for v in values]

            fig = go.Figure(go.Bar(
                x=dates, y=values,
                marker_color=colors,
                text=texts, textposition="outside",
                textfont=dict(size=9),
            ))
            fig.update_layout(
                title=dict(text=sel_entity, font=dict(size=11, color="#1A1A1A"), x=0),
                height=310,
                margin=dict(l=0, r=10, t=32, b=50),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
                yaxis=dict(showgrid=True, gridcolor="#F0EDE9",
                           zeroline=True, zerolinecolor="#E8E4DE"),
                font=dict(size=10, color="#1A1A1A"),
            )
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})


# ── 입력관리 ──────────────────────────────────────────────────────────────────

def _render_input_page():
    today     = date.today()
    yesterday = today - timedelta(days=1)

    col_main, col_side = st.columns([2.2, 1.1])

    with col_main:
        st.markdown(
            '<p style="font-size:1.13rem;font-weight:600;color:#1A1A1A;margin:0 0 2px;">'
            '손익 입력</p>'
            '<p style="font-size:0.75rem;color:#5C5C5C;margin:0 0 20px;">'
            '부서별 전일자 손익을 입력합니다. 부서 PIN 인증 후 저장됩니다.</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<hr style="border:0;border-top:1px solid #e2e8f0;margin:0 0 20px;">',
            unsafe_allow_html=True,
        )

        # 기준일 선택
        trade_date = st.date_input(
            "기준일", value=yesterday, max_value=today,
            key="pnl_input_date", label_visibility="collapsed",
        )
        trade_date_str = str(trade_date)
        st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

        # 부서 옵션
        dept_options = []
        dept_map: dict[str, tuple[str, str]] = {}
        for div, depts in DIVISIONS_STRUCTURE:
            if depts:
                for dept in depts:
                    lbl = f"{div} — {dept}"
                    dept_options.append(lbl)
                    dept_map[lbl] = (div, dept)
            else:
                dept_options.append(div)
                dept_map[div] = (div, div)

        # 입력 폼
        st.markdown(
            '<p style="font-size:0.83rem;font-weight:600;color:#1A1A1A;margin:0 0 8px;">'
            '손익 입력</p>',
            unsafe_allow_html=True,
        )
        with st.form("pnl_entry_form", clear_on_submit=False):
            c1, c2 = st.columns([3, 2])
            with c1:
                sel_dept_lbl = st.selectbox(
                    "부서 선택", dept_options,
                    key="pnl_dept_sel", label_visibility="collapsed",
                )
            with c2:
                pin_input = st.text_input(
                    "PIN", max_chars=4, type="password",
                    placeholder="PIN 4자리 입력", label_visibility="collapsed",
                )

            pnl_input = st.number_input(
                "손익 (백만원)", value=0.0, step=1.0, format="%.1f",
                key="pnl_amount_input", label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "입력 확인", type="primary", use_container_width=True,
            )

        if submitted:
            sel_div, sel_dept = dept_map[sel_dept_lbl]
            if not pin_input or len(pin_input) != 4 or not pin_input.isdigit():
                st.error("PIN은 4자리 숫자여야 합니다.")
            elif not db.verify_pnl_pin(sel_div, sel_dept, pin_input):
                st.error("PIN이 올바르지 않습니다.")
            else:
                db.upsert_pnl_entry(trade_date_str, sel_div, sel_dept, pnl_input)
                sign = "+" if pnl_input >= 0 else ""
                st.success(
                    f"{sel_dept_lbl} — {trade_date_str} "
                    f"손익 {sign}{pnl_input:,.1f} 백만원 저장 완료"
                )
                st.rerun()

        # 입력 현황 그리드
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:0.83rem;font-weight:600;color:#1A1A1A;margin:0 0 8px;">'
            f'입력 현황 <span style="font-size:0.75rem;color:#9A9690;font-weight:400;">'
            f'— {trade_date_str}</span></p>',
            unsafe_allow_html=True,
        )
        _render_input_status(trade_date_str)

        # PIN 관리 (관리자)
        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        with st.expander("PIN 관리"):
            st.markdown(
                '<p style="font-size:0.78rem;color:#888;margin-bottom:12px;">'
                '현재 PIN을 알아야 변경 가능합니다. 초기 PIN은 <b>0000</b>입니다.</p>',
                unsafe_allow_html=True,
            )
            with st.form("pin_change_form", clear_on_submit=True):
                pm_dept = st.selectbox(
                    "부서", dept_options,
                    key="pm_dept", label_visibility="collapsed",
                )
                pc1, pc2 = st.columns(2)
                with pc1:
                    pm_old = st.text_input(
                        "현재 PIN", max_chars=4, type="password",
                        placeholder="현재 PIN", label_visibility="collapsed",
                    )
                with pc2:
                    pm_new = st.text_input(
                        "새 PIN", max_chars=4, type="password",
                        placeholder="새 PIN (4자리)", label_visibility="collapsed",
                    )
                pm_confirm = st.text_input(
                    "새 PIN 확인", max_chars=4, type="password",
                    placeholder="새 PIN 확인", label_visibility="collapsed",
                )
                pm_submitted = st.form_submit_button("PIN 변경", type="primary")

            if pm_submitted:
                pm_div, pm_dep = dept_map[pm_dept]
                if not pm_old or not pm_old.isdigit() or len(pm_old) != 4:
                    st.error("현재 PIN을 4자리 숫자로 입력해주세요.")
                elif not db.verify_pnl_pin(pm_div, pm_dep, pm_old):
                    st.error("현재 PIN이 올바르지 않습니다.")
                elif not pm_new or not pm_new.isdigit() or len(pm_new) != 4:
                    st.error("새 PIN은 4자리 숫자여야 합니다.")
                elif pm_new != pm_confirm:
                    st.error("새 PIN이 일치하지 않습니다.")
                else:
                    db.set_pnl_pin(pm_div, pm_dep, pm_new)
                    st.success(f"{pm_dept} PIN이 변경되었습니다.")

        # 엑셀 일괄 업로드
        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        with st.expander("엑셀 일괄 업로드"):
            _render_bulk_upload()

    with col_side:
        entries      = db.get_pnl_entries_by_date(trade_date_str)
        entered_cnt  = len(entries)
        total_units  = len(ALL_UNITS)
        pct          = entered_cnt / total_units if total_units else 0

        st.markdown(
            '<p style="font-size:1.13rem;font-weight:600;color:#1A1A1A;margin:0 0 2px;">'
            '입력 현황</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="font-size:0.75rem;color:#5C5C5C;margin:0 0 20px;">'
            f'{trade_date_str} 기준</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<hr style="border:0;border-top:1px solid #e2e8f0;margin:0 0 20px;">',
            unsafe_allow_html=True,
        )

        # 전체 카운터
        st.markdown(
            f'<div style="text-align:center;padding:10px 0 18px;">'
            f'<div style="font-size:2.2rem;font-weight:700;color:#1A1A1A;">'
            f'{entered_cnt}'
            f'<span style="font-size:1rem;color:#9A9690;font-weight:400;"> / {total_units}</span>'
            f'</div>'
            f'<div style="font-size:0.75rem;color:#5C5C5C;margin-top:4px;">부서 입력 완료</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.progress(pct)
        st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

        # 부문별 현황
        for div, depts in DIVISIONS_STRUCTURE:
            keys    = [(div, d) for d in depts] if depts else [(div, div)]
            done    = sum(1 for k in keys if k in entries)
            total_k = len(keys)
            all_done = done == total_k
            color = "#15803d" if all_done else ("#f59e0b" if done > 0 else "#94a3b8")
            icon  = "●" if all_done else ("◐" if done > 0 else "○")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:6px 0;border-bottom:1px solid #F0EDE9;">'
                f'<span style="font-size:0.82rem;color:#4A4A4A;">{div}</span>'
                f'<span style="font-size:0.78rem;color:{color};font-weight:600;">'
                f'{icon} {done}/{total_k}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_input_status(trade_date_str: str):
    """입력 현황 테이블"""
    entries  = db.get_pnl_entries_by_date(trade_date_str)
    rows_html = ""

    for div, depts in DIVISIONS_STRUCTURE:
        if depts:
            for dept in depts:
                k       = (div, dept)
                v       = entries.get(k)
                entered = v is not None
                if entered:
                    v_color = "#15803d" if v >= 0 else "#b91c1c"
                    s       = "+" if v > 0 else ""
                    val_str = f'<span style="color:{v_color};font-weight:600;">{s}{v:,.0f}</span>'
                    chk     = '<span style="color:#15803d;font-weight:700;">✓</span>'
                else:
                    val_str = '<span style="color:#94a3b8;">미입력</span>'
                    chk     = '<span style="color:#94a3b8;">—</span>'

                rows_html += (
                    f'<tr>'
                    f'<td style="padding:8px 12px;font-size:14px;color:#5A5A5A;">{div}</td>'
                    f'<td style="padding:8px 12px;font-size:14px;color:#1A1A1A;">{dept}</td>'
                    f'<td style="padding:8px 12px;text-align:center;font-size:14px;">{chk}</td>'
                    f'<td style="padding:8px 12px;text-align:right;font-size:14px;">{val_str}</td>'
                    f'</tr>'
                )
        else:
            k       = (div, div)
            v       = entries.get(k)
            entered = v is not None
            if entered:
                v_color = "#15803d" if v >= 0 else "#b91c1c"
                s       = "+" if v > 0 else ""
                val_str = f'<span style="color:{v_color};font-weight:600;">{s}{v:,.0f}</span>'
                chk     = '<span style="color:#15803d;font-weight:700;">✓</span>'
            else:
                val_str = '<span style="color:#94a3b8;">미입력</span>'
                chk     = '<span style="color:#94a3b8;">—</span>'

            rows_html += (
                f'<tr style="background:#F7F5F2;">'
                f'<td style="padding:8px 12px;font-size:14px;font-weight:600;'
                f'color:#1A1A1A;" colspan="2">{div}</td>'
                f'<td style="padding:8px 12px;text-align:center;font-size:14px;">{chk}</td>'
                f'<td style="padding:8px 12px;text-align:right;font-size:14px;">{val_str}</td>'
                f'</tr>'
            )

    st.markdown(f"""
<style>
.pnl-status-table {{
    width:100%; border-collapse:collapse;
    border:1px solid #E8E4DE; border-radius:6px; overflow:hidden; font-family:inherit;
}}
.pnl-status-table th {{
    background:#F0EDE9; color:#1A1A1A;
    padding:10px 12px; font-size:0.75rem; font-weight:600;
    letter-spacing:0.03em; border-bottom:2px solid #D4CFC9;
}}
.pnl-status-table td {{ border-top:1px solid #E8E4DE; }}
.pnl-status-table tr:hover td {{ background:#FAF8F5 !important; }}
</style>
<table class="pnl-status-table">
  <thead>
    <tr>
      <th style="width:24%;text-align:left;">부문</th>
      <th style="width:36%;text-align:left;">본부</th>
      <th style="width:10%;text-align:center;">입력</th>
      <th style="width:30%;text-align:right;">손익 (백만원)</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)


# ── 엑셀 일괄 업로드 ──────────────────────────────────────────────────────────

def _render_bulk_upload():
    import io
    import pandas as pd

    _VALID_UNITS = set(ALL_UNITS)  # {(division, department), ...}

    st.markdown(
        '<p style="font-size:0.78rem;color:#888;margin-bottom:10px;">'
        '과거 손익 데이터를 엑셀로 한꺼번에 업로드합니다. '
        '기존 데이터와 날짜·부문·본부가 겹치면 덮어씁니다.</p>',
        unsafe_allow_html=True,
    )

    # 템플릿 다운로드
    sample_rows = []
    for div, depts in DIVISIONS_STRUCTURE:
        units = [(div, d) for d in depts] if depts else [(div, div)]
        for d, dept in units:
            sample_rows.append({"날짜": "2026-01-02", "부문": div, "본부": dept, "손익": 0.0})
    tpl_buf = io.BytesIO()
    pd.DataFrame(sample_rows).to_excel(tpl_buf, index=False)
    tpl_buf.seek(0)
    st.download_button(
        "템플릿 다운로드 (.xlsx)", tpl_buf,
        file_name="pnl_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "엑셀 파일 선택", type=["xlsx", "xls"],
        label_visibility="collapsed", key="pnl_bulk_upload",
    )
    if uploaded is None:
        return

    # 파일 읽기
    try:
        df_raw = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")
        return

    # 열 이름 정규화
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    rename = {"날짜": "trade_date", "부문": "division", "본부": "department", "손익": "pnl_daily"}
    df_raw = df_raw.rename(columns={k: v for k, v in rename.items() if k in df_raw.columns})

    missing = {"trade_date", "division", "department", "pnl_daily"} - set(df_raw.columns)
    if missing:
        st.error(f"필수 열 없음: {', '.join(missing)}  (필요: 날짜 / 부문 / 본부 / 손익)")
        return

    # 행별 검증
    valid_rows, errors = [], []
    for i, row in df_raw.iterrows():
        row_num = i + 2  # 헤더 포함 엑셀 기준

        # 날짜
        raw_date = row["trade_date"]
        try:
            if hasattr(raw_date, "strftime"):
                trade_date = raw_date.strftime("%Y-%m-%d")
            else:
                trade_date = str(raw_date).strip()[:10]
            date.fromisoformat(trade_date)
        except Exception:
            errors.append(f"행 {row_num}: 날짜 형식 오류 ({raw_date!r})")
            continue

        # 부문/본부
        division   = str(row["division"]).strip()
        department = str(row["department"]).strip()
        if (division, department) not in _VALID_UNITS:
            errors.append(f"행 {row_num}: 부문·본부 없음 ({division} / {department})")
            continue

        # 손익
        try:
            pnl = float(row["pnl_daily"])
        except Exception:
            errors.append(f"행 {row_num}: 손익 값 오류 ({row['pnl_daily']!r})")
            continue

        valid_rows.append({
            "trade_date": trade_date, "division": division,
            "department": department, "pnl_daily": pnl,
        })

    # 오류 표시
    if errors:
        with st.expander(f"오류 {len(errors)}건", expanded=True):
            for e in errors[:20]:
                st.caption(e)
            if len(errors) > 20:
                st.caption(f"... 외 {len(errors) - 20}건")

    if not valid_rows:
        st.warning("유효한 데이터가 없습니다.")
        return

    # 미리보기 요약
    vdf = pd.DataFrame(valid_rows)
    date_min, date_max = vdf["trade_date"].min(), vdf["trade_date"].max()
    st.markdown(
        f'<p style="font-size:0.82rem;color:#1A1A1A;margin:10px 0 6px;">'
        f'유효 <b>{len(valid_rows)}건</b> &nbsp;·&nbsp; '
        f'기간 <b>{date_min}</b> ~ <b>{date_max}</b></p>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        vdf.rename(columns={"trade_date": "날짜", "division": "부문",
                             "department": "본부", "pnl_daily": "손익"}),
        use_container_width=True, hide_index=True, height=200,
    )

    # 업로드 확인
    if st.button("전체 업로드 확인", type="primary", key="pnl_bulk_confirm"):
        for r in valid_rows:
            db.upsert_pnl_entry(r["trade_date"], r["division"], r["department"], r["pnl_daily"])
        st.success(f"{len(valid_rows)}건 저장 완료")
        st.rerun()
