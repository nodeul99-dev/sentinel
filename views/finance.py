"""
재무건전성 비율 모니터링 페이지
"""
import json

import streamlit as st

import db
from api.fss_api import collect_all_securities_data
from config import COLORS
from core.constants import FSS_DATA_SOURCES, NCR_METRIC_LABELS

# 표시할 분기 목록 (최신 순)
QUARTERS = [
    "2025Q3", "2025Q2", "2025Q1",
    "2024Q4", "2024Q3", "2024Q2", "2024Q1",
    "2023Q4",
]


def render(subpage: str = None):
    if subpage == "trends":
        _render_trends()
    elif subpage == "data":
        _render_data_management()
    else:
        _render_dashboard()


# ── 대시보드 ────────────────────────────────────────────────────────────────

DASHBOARD_QUARTER = "2025Q3"


def _render_dashboard():
    data = db.get_fss_data(DASHBOARD_QUARTER, "ncr_data")

    col_main, col_side = st.columns([2.2, 1.1])

    with col_main:
        st.markdown(
            '<p style="font-size:1.13rem;font-weight:600;color:#14532d;margin:0 0 14px;">'
            f'국내 증권사 건전성지표 <span style="font-size:0.85rem;font-weight:400;color:#888;">({DASHBOARD_QUARTER} 기준 · 단위: 억원, 연결재무제표)</span></p>',
            unsafe_allow_html=True,
        )

        if not data:
            st.warning(
                f"**{DASHBOARD_QUARTER}** 데이터가 없습니다. "
                "사이드바의 **데이터관리** 메뉴에서 수집해주세요."
            )
        else:
            _render_ranking_table(data)

    with col_side:
        _render_company_detail(data or [])


def _render_ranking_table(data: list[dict]):
    import streamlit.components.v1 as components

    # 자기자본 내림차순 정렬 (초기 순위 기준)
    rows = sorted(data, key=lambda x: x["metrics"].get("equity_capital", 0), reverse=True)

    js_data = []
    for i, item in enumerate(rows, 1):
        m = item["metrics"]
        js_data.append({
            "rank":   i,
            "name":   item["company_name"],
            "eq":     m.get("equity_capital", 0),
            "op":     m.get("operating_net_capital", 0),
            "ncr":    m.get("ncr", 0),
            "oncr":   m.get("old_ncr", 0),
            "risk":   m.get("total_risk", 0),
        })

    selected_company = st.query_params.get("company", "")
    table_height = 44 + len(rows) * 38 + 20

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin:0; padding:0; font-family: inherit; background: transparent; }}
  .fin-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95rem;
    table-layout: fixed;
  }}
  .fin-table colgroup col:nth-child(1) {{ width: 5%; }}
  .fin-table colgroup col:not(:nth-child(1)) {{ width: calc(95% / 6); }}
  .fin-table th {{
    background: #4a7c59;
    color: #ffffff;
    padding: 11px 8px;
    text-align: center;
    font-weight: 600;
    font-size: 0.95rem;
    border: none;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
  }}
  .fin-table th:hover {{ background: #3d6b4a; }}
  .fin-table th .sort-icon {{
    display: inline-block;
    margin-left: 4px;
    font-size: 0.75rem;
    opacity: 0.7;
  }}
  .fin-table td {{
    padding: 9px 10px;
    border-top: 1px solid #d1e8d4;
    font-size: 0.95rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }}
  .fin-table tr:nth-child(even) td {{ background: #f8fffe; }}
  .fin-table tr:hover td {{ background: #f0fdf4 !important; }}
  .fin-table tr.selected td {{ background: #bbf7d0 !important; }}
  .fin-table td.center {{ text-align: center; }}
  .fin-table td.left   {{ text-align: left; }}
  .fin-table td.right  {{ text-align: right; }}
</style>
</head>
<body>
<div style="overflow-x:auto;">
<table class="fin-table" id="finTable">
  <colgroup><col/><col/><col/><col/><col/><col/><col/></colgroup>
  <thead>
    <tr>
      <th onclick="sortTable(0)" data-col="0">순위<span class="sort-icon">⇅</span></th>
      <th onclick="sortTable(1)" data-col="1">회사명<span class="sort-icon">⇅</span></th>
      <th onclick="sortTable(2)" data-col="2">자기자본<span class="sort-icon">⇅</span></th>
      <th onclick="sortTable(3)" data-col="3">영업용순자본<span class="sort-icon">⇅</span></th>
      <th onclick="sortTable(4)" data-col="4">NCR<span class="sort-icon">⇅</span></th>
      <th onclick="sortTable(5)" data-col="5">구NCR<span class="sort-icon">⇅</span></th>
      <th onclick="sortTable(6)" data-col="6">총위험액<span class="sort-icon">⇅</span></th>
    </tr>
  </thead>
  <tbody id="tbody"></tbody>
</table>
</div>

<script>
const RAW = {json.dumps(js_data, ensure_ascii=False)};
const SELECTED = {json.dumps(selected_company, ensure_ascii=False)};
let sortCol = -1;
let sortAsc = true;

function fmt_int(v)  {{ return Number(v).toLocaleString('ko-KR'); }}
function fmt_pct(v)  {{ return Number(v).toLocaleString('ko-KR', {{minimumFractionDigits:1, maximumFractionDigits:1}}) + '%'; }}

function buildRows(data) {{
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  data.forEach(function(d) {{
    const isDS = d.name.includes('DS투자') || d.name.includes('디에스투자');
    const tr = document.createElement('tr');
    if (d.name === SELECTED) tr.classList.add('selected');
    const style = isDS ? ' style="color:#dc2626;font-weight:700;"' : '';
    tr.innerHTML =
      '<td class="center"' + style + '>' + d.rank + '</td>' +
      '<td class="left"'   + style + '>' + d.name + '</td>' +
      '<td class="right"'  + style + '>' + fmt_int(d.eq)   + '</td>' +
      '<td class="right"'  + style + '>' + fmt_int(d.op)   + '</td>' +
      '<td class="right"'  + style + '>' + fmt_pct(d.ncr)  + '</td>' +
      '<td class="right"'  + style + '>' + fmt_pct(d.oncr) + '</td>' +
      '<td class="right"'  + style + '>' + fmt_int(d.risk) + '</td>';
    (function(name) {{
      tr.onclick = function() {{
        try {{
          var sp = new URLSearchParams(window.parent.location.search);
          sp.set('company', name);
          window.parent.location.href = window.parent.location.pathname + '?' + sp.toString();
        }} catch(e) {{}}
      }};
    }})(d.name);
    tbody.appendChild(tr);
  }});
}}

function sortTable(col) {{
  const ths = document.querySelectorAll('.fin-table th');
  if (sortCol === col) {{
    sortAsc = !sortAsc;
  }} else {{
    sortCol = col;
    sortAsc = true;
  }}
  ths.forEach(function(th, i) {{
    th.querySelector('.sort-icon').textContent = (i === col) ? (sortAsc ? '↑' : '↓') : '⇅';
  }});

  const colKeys = ['rank','name','eq','op','ncr','oncr','risk'];
  const key = colKeys[col];
  const sorted = RAW.slice().sort(function(a, b) {{
    const av = a[key], bv = b[key];
    if (typeof av === 'number') return sortAsc ? av - bv : bv - av;
    return sortAsc ? String(av).localeCompare(String(bv), 'ko') : String(bv).localeCompare(String(av), 'ko');
  }});
  buildRows(sorted);
}}

buildRows(RAW);
</script>
</body>
</html>
"""
    components.html(html, height=table_height, scrolling=False)


# ── 추이 분석 페이지 ─────────────────────────────────────────────────────────

def _render_trends():
    st.markdown(
        '<p style="font-size:0.85rem;font-weight:600;color:#14532d;margin:0 0 12px;">'
        '추이 분석</p>',
        unsafe_allow_html=True,
    )

    available = db.get_available_quarters("ncr_data")
    if len(available) < 2:
        st.info("추이 분석은 2개 이상의 분기 데이터가 필요합니다. 더 많은 분기 데이터를 수집해주세요.")
        return

    # 분기별 평균 NCR 계산
    quarter_avg = {}
    for q in sorted(available):
        data = db.get_fss_data(q, "ncr_data")
        ncr_vals = [d["metrics"].get("ncr", 0) for d in data if d["metrics"].get("ncr", 0) > 0]
        if ncr_vals:
            quarter_avg[q] = round(sum(ncr_vals) / len(ncr_vals), 1)

    if quarter_avg:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(quarter_avg.keys()),
            y=list(quarter_avg.values()),
            mode="lines+markers",
            name="평균 NCR",
            line=dict(color="#a3e635", width=2),
            marker=dict(size=8),
        ))
        fig.add_hline(y=150, line_dash="dash", line_color="#dc2626",
                      annotation_text="150% 기준선")
        fig.update_layout(
            title="분기별 평균 NCR 추이",
            xaxis_title="분기",
            yaxis_title="NCR (%)",
            height=350,
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)


# ── 데이터 관리 페이지 ────────────────────────────────────────────────────────

def _render_data_management():
    st.markdown(
        '<p style="font-size:0.85rem;font-weight:600;color:#14532d;margin:0 0 12px;">'
        '데이터 관리</p>',
        unsafe_allow_html=True,
    )

    # 수동 수집 섹션
    st.markdown("#### 데이터 수집")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        quarter = st.selectbox("분기", QUARTERS, key="mgmt_quarter")
    with col2:
        data_source = st.selectbox(
            "소스",
            list(FSS_DATA_SOURCES.keys()),
            format_func=lambda x: FSS_DATA_SOURCES[x],
            key="mgmt_source",
        )
    with col3:
        st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
        if st.button("수집 시작", type="primary", use_container_width=True):
            _update_fss_data(quarter, data_source)

    st.divider()

    # 업데이트 로그
    st.markdown("#### 수집 로그")
    logs = db.get_fss_update_log(limit=15)
    if not logs:
        st.caption("수집 이력이 없습니다.")
    else:
        rows = []
        for log in logs:
            rows.append({
                "시각": log["updated_at"][:19],
                "분기": log["quarter"],
                "소스": FSS_DATA_SOURCES.get(log["data_source"], log["data_source"]),
                "상태": "✅ 성공" if log["update_status"] == "success" else "❌ 실패",
                "건수": log["items_count"],
                "오류": log.get("error_message") or "",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_company_detail(data: list[dict]):
    st.markdown(
        '<p style="font-size:0.95rem;font-weight:600;color:#14532d;margin:0 0 10px;">회사 상세</p>',
        unsafe_allow_html=True,
    )

    if not data:
        st.caption("데이터가 없습니다.")
        return

    companies = [d["company_name"] for d in data]
    selected = st.query_params.get("company", "")

    if not selected or selected not in companies:
        st.markdown(
            '<p style="font-size:0.82rem;color:#94a3b8;margin-top:20px;">'
            '← 왼쪽 표에서 증권사를 클릭하세요</p>',
            unsafe_allow_html=True,
        )
        return

    item = next((d for d in data if d["company_name"] == selected), None)
    if not item:
        return

    m = item["metrics"]
    is_ds = "DS투자" in selected or "디에스투자" in selected
    name_color = "#dc2626" if is_ds else "#374151"

    def metric_card(label: str, value, is_pct: bool = False):
        if is_pct:
            formatted = f"{value:,.1f}%"
        else:
            formatted = f"{int(value):,}"
        st.markdown(
            f"""<div style="
                background:#ffffff;
                border:1px solid #d1e8d4;
                border-radius:8px;
                padding:10px 14px;
                margin-bottom:8px;
            ">
              <div style="font-size:0.75rem;color:#64748b;margin-bottom:3px;">{label}</div>
              <div style="font-size:1.05rem;font-weight:700;color:#14532d;">{formatted}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<p style="font-size:0.85rem;font-weight:600;color:{name_color};margin:8px 0 10px;">{selected}</p>',
        unsafe_allow_html=True,
    )
    metric_card("NCR", m.get("ncr", 0), is_pct=True)
    metric_card("구NCR", m.get("old_ncr", 0), is_pct=True)
    metric_card("자기자본 (억원)", m.get("equity_capital", 0))
    metric_card("영업용순자본 (억원)", m.get("operating_net_capital", 0))
    metric_card("총위험액 (억원)", m.get("total_risk", 0))
    metric_card("필요유지자기자본 (억원)", m.get("required_equity", 0))


# ── 데이터 갱신 공통 함수 ────────────────────────────────────────────────────

def _update_fss_data(quarter: str, data_source: str):
    with st.spinner(f"{quarter} {FSS_DATA_SOURCES.get(data_source, data_source)} 데이터 수집 중..."):
        try:
            data_list = collect_all_securities_data(quarter, data_source)
            db.save_fss_data(quarter, data_source, data_list)
            db.log_fss_update(data_source, quarter, "success", len(data_list))
            st.success(f"✅ {len(data_list)}개 증권사 데이터 업데이트 완료!")
            st.rerun()
        except Exception as e:
            db.log_fss_update(data_source, quarter, "failed", 0, str(e))
            st.error(f"❌ 수집 실패: {e}")
