"""
재무건전성 비율 모니터링 페이지
"""
import html as _html
import json
from datetime import datetime

import streamlit as st

import db
from api.fss_api import collect_all_securities_data

def _current_quarter() -> str:
    """오늘 날짜 기준 현재 분기 반환. 예: '2026Q1'"""
    now = datetime.now()
    q = (now.month - 1) // 3 + 1
    return f"{now.year}Q{q}"


def _generate_quarters(start_year: int = 2016) -> list[str]:
    """start_year Q1 부터 현재 분기까지 전체 분기 목록 반환 (오래된 순)"""
    now = datetime.now()
    current_q = (now.month - 1) // 3 + 1
    result = []
    for year in range(start_year, now.year + 1):
        max_q = current_q if year == now.year else 4
        for q in range(1, max_q + 1):
            result.append(f"{year}Q{q}")
    return result


def render(subpage: str = None):
    if subpage == "trends":
        _render_trends()
    elif subpage == "data":
        _render_data_management()
    else:
        _render_dashboard()


# ── 대시보드 ────────────────────────────────────────────────────────────────

def _render_dashboard():
    available = db.get_available_quarters("ncr_data")
    dashboard_quarter = available[0] if available else _current_quarter()
    data = db.get_fss_data(dashboard_quarter, "ncr_data")

    col_main, col_side = st.columns([2.2, 1.1])

    with col_main:
        st.markdown(
            '<p style="font-size:1.13rem;font-weight:600;color:#14532d;margin:0 0 14px;">'
            f'국내 증권사 건전성지표 <span style="font-size:0.85rem;font-weight:400;color:#888;">({dashboard_quarter} 기준 · 단위: 억원, 연결재무제표)</span></p>',
            unsafe_allow_html=True,
        )

        if not data:
            st.warning(
                f"**{dashboard_quarter}** 데이터가 없습니다. "
                "사이드바의 **데이터관리** 메뉴에서 수집해주세요."
            )
        else:
            _render_ranking_table(data)

    with col_side:
        _render_company_detail()


def _render_ranking_table(data: list[dict]):
    import pandas as pd
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

    rows = sorted(data, key=lambda x: x["metrics"].get("equity_capital", 0), reverse=True)

    df_rows = []
    for i, item in enumerate(rows, 1):
        m = item["metrics"]
        df_rows.append({
            "순위":       i,
            "회사명":     item["company_name"],
            "자기자본":   m.get("equity_capital", 0),
            "영업용순자본": m.get("operating_net_capital", 0),
            "NCR(%)":     m.get("ncr", 0),
            "구NCR(%)":   m.get("old_ncr", 0),
            "총위험액":   m.get("total_risk", 0),
        })

    df = pd.DataFrame(df_rows)

    num_fmt = JsCode("function(p){return p.value==null?'':Math.round(p.value).toLocaleString('ko-KR');}")
    pct_fmt = JsCode("function(p){return p.value==null?'':p.value.toFixed(1)+'%';}")

    ds_row_style = JsCode("""
    function(params) {
        if (params.data && (
            params.data['회사명'].indexOf('DS투자') >= 0 ||
            params.data['회사명'].indexOf('디에스투자') >= 0
        )) {
            return {'color': '#dc2626', 'fontWeight': 'bold'};
        }
    }
    """)

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_default_column(sortable=True, resizable=False, suppressMovable=True)
    gb.configure_column("순위",       width=58,  suppressSizeToFit=True, type=["numericColumn"])
    gb.configure_column("회사명",     flex=2,    minWidth=100)
    gb.configure_column("자기자본",   flex=1,    minWidth=80, valueFormatter=num_fmt, type=["numericColumn"])
    gb.configure_column("영업용순자본", flex=1,  minWidth=80, valueFormatter=num_fmt, type=["numericColumn"])
    gb.configure_column("NCR(%)",     flex=1,    minWidth=70, valueFormatter=pct_fmt, type=["numericColumn"])
    gb.configure_column("구NCR(%)",   flex=1,    minWidth=70, valueFormatter=pct_fmt, type=["numericColumn"])
    gb.configure_column("총위험액",   flex=1,    minWidth=80, valueFormatter=num_fmt, type=["numericColumn"])
    gb.configure_grid_options(getRowStyle=ds_row_style, rowHeight=34, headerHeight=40)

    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=40 + len(df_rows) * 34 + 16,
        allow_unsafe_jscode=True,
        theme="alpine",
        fit_columns_on_grid_load=True,
    )

    sel = grid_response.selected_rows
    if sel is not None and len(sel) > 0:
        name = sel.iloc[0]["회사명"] if hasattr(sel, "iloc") else sel[0]["회사명"]
        st.session_state["selected_company"] = name


# ── 추이 분석 페이지 ─────────────────────────────────────────────────────────

def _render_trends():
    st.markdown(
        '<p style="font-size:1.13rem;font-weight:600;color:#14532d;margin:0 0 12px;">'
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
        '<p style="font-size:1.13rem;font-weight:600;color:#14532d;margin:0 0 12px;">'
        '데이터 관리</p>',
        unsafe_allow_html=True,
    )

    # ── 최신 데이터 수집 ───────────────────────────────────────────────────────
    st.markdown("#### 최신 데이터 수집")
    current_q = _current_quarter()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"현재 분기: **{current_q}**  ·  수집 후 대시보드에 반영됩니다.")
    with col2:
        if st.button("수집 시작", type="primary", use_container_width=True):
            _update_fss_data(current_q, "ncr_data")

    st.divider()

    available = set(db.get_available_quarters("ncr_data"))
    missing = [q for q in _generate_quarters(2016) if q not in available]

    if available:
        st.caption("※ 수집 로직 변경 후 기존 데이터를 덮어써야 할 경우 아래 버튼을 사용하세요.")
        if st.button("강제 재수집 (최근 1년, 기존 데이터 덮어쓰기)", type="secondary"):
            now = datetime.now()
            one_year_ago = f"{now.year - 1}Q{(now.month - 1) // 3 + 1}"
            force_quarters = sorted(q for q in set(available) | set(missing) if q >= one_year_ago)
            _collect_historical(force_quarters)

    st.divider()

    # ── 수집 로그 ──────────────────────────────────────────────────────────────
    st.markdown("#### 수집 로그")
    logs = db.get_fss_update_log(limit=20)
    if not logs:
        st.caption("수집 이력이 없습니다.")
    else:
        rows = []
        for log in logs:
            rows.append({
                "시각": log["updated_at"][:19],
                "분기": log["quarter"],
                "상태": "✅ 성공" if log["update_status"] == "success" else "❌ 실패",
                "건수": log["items_count"],
                "오류": log.get("error_message") or "",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_company_detail():
    import streamlit.components.v1 as components

    selected = st.session_state.get("selected_company", "")

    st.markdown(
        '<p style="font-size:1.13rem;font-weight:600;color:#14532d;margin:0 0 6px;">회사 상세</p>',
        unsafe_allow_html=True,
    )

    if not selected:
        st.markdown(
            '<p style="font-size:0.82rem;color:#94a3b8;margin-top:20px;">'
            '← 왼쪽 표에서 증권사를 클릭하세요</p>',
            unsafe_allow_html=True,
        )
        return

    history = db.get_company_history(selected, "ncr_data", n=4)
    if not history:
        st.caption("데이터가 없습니다.")
        return

    display_history = history

    is_ds = "DS투자" in selected or "디에스투자" in selected
    name_color = "#dc2626" if is_ds else "#0f172a"

    js_data = [
        {
            "quarter":         item["quarter"],
            "equity_capital":  item["metrics"].get("equity_capital", 0),
            "net_income_q":    item["metrics"].get("net_income_q"),
            "ncr":             item["metrics"].get("ncr", 0),
            "old_ncr":         item["metrics"].get("old_ncr", 0),
            "total_risk":      item["metrics"].get("total_risk", 0),
            "required_equity": item["metrics"].get("required_equity", 0),
        }
        for item in display_history
    ]

    components.html(_build_detail_html(selected, name_color, js_data), height=620, scrolling=False)


def _build_detail_html(company: str, name_color: str, js_data: list) -> str:
    esc = _html.escape(company)
    n_q = len(js_data)
    data_json = json.dumps(js_data, ensure_ascii=False)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:transparent;color:#334155}}
.cname{{font-size:1.14rem;font-weight:700;color:{name_color};margin-bottom:2px}}
.csub{{font-size:.87rem;color:#94a3b8;margin-bottom:10px}}
.mc{{display:flex;align-items:center;padding:8px 0;border-bottom:1px solid #f1f5f9}}
.mc:last-child{{border-bottom:none}}
.ml{{flex:0 0 52%;min-width:0}}
.mlb{{font-size:.87rem;color:#94a3b8;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.mlv{{font-size:1.14rem;font-weight:700;color:#14532d;white-space:nowrap}}
.mr{{flex:0 0 48%;display:flex;justify-content:flex-end;align-items:center;padding-right:32px}}
</style></head><body>
<div class="cname">{esc}</div>
<div class="csub">최근 {n_q}개 분기 추이</div>
<div id="cards"></div>
<script>
var DATA={data_json};
var METRICS=[
  {{key:'equity_capital', label:'자기자본',          unit:'억원',pct:false}},
  {{key:'net_income_q',   label:'당기순이익 (분기)', unit:'억원',pct:false}},
  {{key:'ncr',            label:'NCR',              unit:'%',  pct:true }},
  {{key:'old_ncr',        label:'구NCR',            unit:'%',  pct:true }},
  {{key:'total_risk',     label:'총위험액',           unit:'억원',pct:false}},
  {{key:'required_equity',label:'필요유지자기자본',  unit:'억원',pct:false}},
];
function fmt(v,pct){{
  if(v===null||v===undefined)return 'N/A';
  if(pct)return v.toLocaleString('ko-KR',{{minimumFractionDigits:1,maximumFractionDigits:1}})+'%';
  return Math.round(v).toLocaleString('ko-KR')+'억원';
}}
function fmtSpark(v,pct){{
  if(v===null||v===undefined)return '';
  if(pct)return v.toLocaleString('ko-KR',{{minimumFractionDigits:1,maximumFractionDigits:1}})+'%';
  return Math.round(v).toLocaleString('ko-KR');
}}
function makeSpark(vals,pct){{
  var W=120,H=60,LP=4,RP=4,TP=16,BP=14;
  var svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width',W);svg.setAttribute('height',H);
  svg.setAttribute('viewBox','0 0 '+W+' '+H);
  svg.style.overflow='visible';
  var n=vals.length;
  if(!n)return svg;
  var nonNull=vals.filter(function(d){{return d.v!==null&&d.v!==undefined;}});
  if(!nonNull.length)return svg;
  var vs=nonNull.map(function(d){{return d.v;}});
  var minV=Math.min.apply(null,vs),maxV=Math.max.apply(null,vs);
  var rng=maxV-minV||1;
  var xs=vals.map(function(_,i){{return n===1?W/2:LP+i*(W-LP-RP)/(n-1);}});
  var ys=vals.map(function(d){{
    return(d.v!==null&&d.v!==undefined)?TP+(1-(d.v-minV)/rng)*(H-TP-BP):null;
  }});
  var ptStr='',nnc=0;
  xs.forEach(function(x,i){{if(ys[i]!==null){{ptStr+=x+','+ys[i]+' ';nnc++;}}}});
  if(nnc>1){{
    var pl=document.createElementNS('http://www.w3.org/2000/svg','polyline');
    pl.setAttribute('points',ptStr.trim());
    pl.setAttribute('fill','none');pl.setAttribute('stroke','#a3e635');
    pl.setAttribute('stroke-width','1.5');pl.setAttribute('stroke-linejoin','round');
    svg.appendChild(pl);
  }}
  vals.forEach(function(d,i){{
    var t=document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x',xs[i]);t.setAttribute('y',H-1);
    t.setAttribute('text-anchor','middle');
    t.setAttribute('font-size','9');t.setAttribute('fill','#94a3b8');
    t.textContent=d.q.slice(2);
    svg.appendChild(t);
  }});
  vals.forEach(function(d,i){{
    if(ys[i]===null)return;
    var isLatest=(i===n-1);
    var vl=document.createElementNS('http://www.w3.org/2000/svg','text');
    var above=(ys[i]>H/2);
    vl.setAttribute('x',xs[i]);
    vl.setAttribute('y',above?ys[i]-8:ys[i]+12);
    var anchor=xs[i]>W*0.65?'end':(xs[i]<W*0.35?'start':'middle');
    vl.setAttribute('text-anchor',anchor);
    vl.setAttribute('font-size','10');
    vl.setAttribute('fill',isLatest?'#14532d':'#475569');
    vl.setAttribute('font-weight',isLatest?'700':'400');
    vl.setAttribute('pointer-events','none');
    vl.textContent=fmtSpark(d.v,pct);
    vl.style.display=isLatest?'':'none';
    svg.appendChild(vl);
    var c=document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx',xs[i]);c.setAttribute('cy',ys[i]);
    c.setAttribute('r',isLatest?5:4);
    c.setAttribute('fill',isLatest?'#4d7c0f':'#a3e635');
    c.setAttribute('stroke','#ffffff');c.setAttribute('stroke-width','1.5');
    c.style.cursor=isLatest?'default':'pointer';
    if(!isLatest){{
      (function(lbl){{
        c.addEventListener('mouseover',function(){{lbl.style.display='';}});
        c.addEventListener('mouseout',function(){{lbl.style.display='none';}});
      }})(vl);
    }}
    svg.appendChild(c);
  }});
  return svg;
}}
var container=document.getElementById('cards');
var latest=DATA[DATA.length-1]||{{}};
METRICS.forEach(function(m){{
  var card=document.createElement('div');card.className='mc';
  var left=document.createElement('div');left.className='ml';
  var lbl=document.createElement('div');lbl.className='mlb';
  lbl.textContent=m.label;
  var val=document.createElement('div');val.className='mlv';
  val.textContent=fmt(latest[m.key],m.pct);
  left.appendChild(lbl);left.appendChild(val);
  var right=document.createElement('div');right.className='mr';
  var sv=DATA.map(function(d){{return{{q:d.quarter,v:d[m.key]!==undefined?d[m.key]:null}};}});
  right.appendChild(makeSpark(sv,m.pct));
  card.appendChild(left);card.appendChild(right);
  container.appendChild(card);
}});
</script></body></html>"""


# ── 데이터 갱신 공통 함수 ────────────────────────────────────────────────────

def _fmt_quarter(q: str) -> str:
    """'2025Q3' → '2025년 3분기'"""
    return f"{q[:4]}년 {q[5]}분기"


def _collect_historical(quarters: list[str]):
    """미수집(또는 강제 재수집) 분기를 순서대로 수집. 오래된 것부터."""
    total = len(quarters)
    progress = st.progress(0, text="이력 수집 준비 중...")
    status = st.empty()
    success_cnt, fail_cnt = 0, 0

    for i, q in enumerate(quarters):
        status.markdown(f"`{q}` 수집 중... ({i + 1}/{total})")
        try:
            data_list = collect_all_securities_data(q)
            if data_list:
                db.save_fss_data(q, "ncr_data", data_list)
                db.log_fss_update("ncr_data", q, "success", len(data_list))
                success_cnt += 1
            else:
                db.log_fss_update("ncr_data", q, "success", 0)
        except Exception as e:
            db.log_fss_update("ncr_data", q, "failed", 0, str(e))
            fail_cnt += 1
        progress.progress((i + 1) / total, text=f"{i + 1}/{total} 완료")

    status.empty()
    progress.empty()

    latest = db.get_available_quarters("ncr_data")
    if latest:
        msg = f"✅ {_fmt_quarter(latest[0])}까지 최신 자료를 모두 수집했습니다."
        if fail_cnt:
            msg += f" (실패 {fail_cnt}개 분기)"
        st.success(msg)
    else:
        st.warning("수집된 데이터가 없습니다.")
    st.rerun()


def _update_fss_data(quarter: str, data_source: str):
    """현재 분기부터 최대 4분기 거슬러 올라가며 데이터가 있는 최신 분기를 수집."""
    all_q = _generate_quarters(2016)
    # 지정 분기 이하를 최신순으로 최대 4개 시도
    candidates = [q for q in reversed(all_q) if q <= quarter][:4]

    found_quarter = None
    with st.spinner("최신 데이터 조회 중..."):
        for q in candidates:
            try:
                data_list = collect_all_securities_data(q)
                if data_list:
                    db.save_fss_data(q, data_source, data_list)
                    db.log_fss_update(data_source, q, "success", len(data_list))
                    found_quarter = q
                    break
                else:
                    db.log_fss_update(data_source, q, "success", 0)
            except Exception as e:
                db.log_fss_update(data_source, q, "failed", 0, str(e))

    if found_quarter:
        st.success(f"✅ {_fmt_quarter(found_quarter)}까지 최신 자료를 모두 수집했습니다.")
        st.rerun()
    else:
        st.error("수집 가능한 데이터가 없습니다. 잠시 후 다시 시도해주세요.")
