"""
FSS FISIS API 연동 모듈 (collector.py + utils.py 통합)
"""
import json
import re
import ssl
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests

from config import FSS_API_KEY

# SSL 경고 억제
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ── SSL 어댑터 ──────────────────────────────────────────────────────────────
class LegacyAdapter(requests.adapters.HTTPAdapter):
    """FSS API 등 구형 SSL/TLS 서버 대응 어댑터"""
    def init_poolmanager(self, connections, maxsize, block=False):
        try:
            ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        except AttributeError:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )


def get_session() -> requests.Session:
    """LegacyAdapter가 마운트된 세션 반환"""
    session = requests.Session()
    session.mount('https://', LegacyAdapter())
    return session


# ── 국내 증권사 필터 ────────────────────────────────────────────────────────
FOREIGN_KEYWORDS = [
    "노무라", "씨티그룹", "한국 에스지", "한국스탠다드차타드",
    "맥쿼리", "씨엘에스에이", "도이치", "다이와",
    "한국아이엠씨", "CMS", "케이아이디비", "비엔피파리바",
    "상하이", "모간", "골드만", "메릴린치", "뱅크오브아메리카"
]


def is_domestic_company(company_info: dict) -> bool:
    name = company_info.get('finance_nm', '')
    path = company_info.get('finance_path', '')
    if "[폐]" in name:
        return False
    if any(k in name for k in FOREIGN_KEYWORDS):
        return False
    if "국내증권사" in path:
        return True
    return False


# ── 분기 문자열 파싱 ────────────────────────────────────────────────────────
def quarter_to_month(quarter: str) -> str:
    """
    "2024Q3" → "202409" (분기 끝달)
    Q1→03, Q2→06, Q3→09, Q4→12
    """
    year = quarter[:4]
    q = int(quarter[5])
    month = str(q * 3).zfill(2)
    return f"{year}{month}"


# ── 증권사 목록 조회 ────────────────────────────────────────────────────────
def fetch_company_list(session: requests.Session) -> List[dict]:
    url = (
        f"http://fisis.fss.or.kr/openapi/companySearch.json"
        f"?lang=kr&auth={FSS_API_KEY}&partDiv=F"
    )
    try:
        res = session.get(url, timeout=10)
        data = res.json()
        if data['result']['err_cd'] == '000':
            return [c for c in data['result']['list'] if is_domestic_company(c)]
        return []
    except Exception:
        return []


# ── 개별 증권사 NCR 데이터 수집 ─────────────────────────────────────────────
def fetch_ncr_data(session: requests.Session, company: dict, start_mm: str, end_mm: str) -> Optional[dict]:
    """
    FSS SF408 (연결NCR), SF304 (자본), SF308 (개별NCR) 순으로 조회.
    Returns: metrics dict or None
    """
    finance_cd = company['finance_cd']
    raw_name = company['finance_nm']
    finance_nm = re.sub(r'\(주\)|주식회사|\s+', ' ', raw_name).strip()

    result = {
        "ncr": 0,
        "equity_capital": 0,
        "total_risk": 0,
        "required_equity": 0,
        "operating_net_capital": 0,
        "old_ncr": 0,
        "net_income_q": None,
    }

    def _get(list_no: str) -> Optional[dict]:
        url = (
            f"http://fisis.fss.or.kr/openapi/statisticsInfoSearch.json"
            f"?lang=kr&auth={FSS_API_KEY}&financeCd={finance_cd}"
            f"&listNo={list_no}&term=Q&startBaseMm={start_mm}&endBaseMm={end_mm}"
        )
        try:
            res = session.get(url, timeout=10)
            data = res.json()
            if data['result']['err_cd'] == '000':
                return data['result']['list']
            return None
        except Exception:
            return None

    # SF408 (연결 순자본비율)
    rows = _get("SF408")
    if rows:
        for row in rows:
            ac = row['account_cd']
            val = float(row['a']) if row['a'] else 0
            if ac == 'E':   result['ncr'] = val
            elif ac == 'B': result['total_risk'] = int(val / 100000000)
            elif ac == 'D': result['required_equity'] = int(val / 100000000)
            elif ac == 'A': result['operating_net_capital'] = int(val / 100000000)
            elif ac == 'A1': result['equity_capital'] = int(val / 100000000)

    # SF304 (자본총계)
    rows = _get("SF304")
    if rows:
        for row in rows:
            if row['account_cd'] == 'L':
                val = float(row['a']) if row['a'] else 0
                result['equity_capital'] = int(val / 100000000)
                break

    # Fallback: SF308 (개별)
    if result['ncr'] == 0 or result['equity_capital'] == 0:
        rows = _get("SF308")
        if rows:
            for row in rows:
                ac = row['account_cd']
                val = float(row['a']) if row['a'] else 0
                if result['ncr'] == 0:
                    if ac == 'E':   result['ncr'] = val
                    elif ac == 'B': result['total_risk'] = int(val / 100000000)
                    elif ac == 'D': result['required_equity'] = int(val / 100000000)
                    elif ac == 'A': result['operating_net_capital'] = int(val / 100000000)
                if result['equity_capital'] == 0 and ac == 'A1':
                    result['equity_capital'] = int(val / 100000000)

    # 구NCR 계산
    if result['total_risk'] > 0:
        result['old_ncr'] = round(
            (result['operating_net_capital'] / result['total_risk']) * 100, 2
        )

    # 당기순이익(분기 단독): SF307 'a' 컬럼 = 당분기값 직접 사용
    rows_inc = _get("SF307")
    if rows_inc:
        for row in rows_inc:
            if row.get('account_cd') == 'J':
                val_a = float(row['a']) if row.get('a') else None
                if val_a is not None:
                    result['net_income_q'] = int(val_a / 100000000)
                break

    # 데이터 없으면 None
    if result['equity_capital'] == 0 and result['ncr'] == 0:
        print(f"  [SKIP] {finance_nm}: 데이터 없음")
        return None

    return {
        "company_code": finance_cd,
        "company_name": finance_nm,
        "metrics": result,
    }


# ── 전체 증권사 데이터 수집 ──────────────────────────────────────────────────
def collect_all_securities_data(quarter: str) -> List[dict]:
    """
    Args:
        quarter: "2024Q3" 형식

    Returns:
        [{"company_code": ..., "company_name": ..., "metrics": {...}}, ...]
    """
    mm = quarter_to_month(quarter)
    session = get_session()

    companies = fetch_company_list(session)

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_ncr_data, session, c, mm, mm): c
            for c in companies
        }
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    return results
