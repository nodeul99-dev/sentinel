# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 실행

```bash
cd C:\projects_openclaw\sentinel_ds
streamlit run app.py
```

접속: http://localhost:8501

의존성 설치:
```bash
pip install -r requirements.txt
```

## 환경변수 (.env)

```
LAW_API_KEY=...   # 법제처 오픈API (https://open.law.go.kr)
FSS_API_KEY=...   # 금감원 FISIS (없으면 config.py fallback 사용)
```

## 아키텍처

`app.py`가 진입점이며, URL 쿼리 파라미터(`?page=`, `?subpage=`)로 라우팅한다. `pages/` 폴더는 사용하지 않고 `views/`를 수동으로 import한다.

### 레이어 구조

| 레이어 | 역할 |
|--------|------|
| `app.py` | 전역 CSS, 상단바, 사이드바, 라우팅 |
| `views/` | 각 페이지 UI (`render()` 함수 하나씩 export) |
| `api/` | 외부 API 연동 (법제처, 금감원 FISIS) |
| `utils/` | PDF 파싱, 검색 로직, 하이라이트 |
| `db.py` | SQLite 단일 모듈 (규정검색 + FSS 테이블) |
| `config.py` | DB 경로, API 키, 색상/레이아웃 상수 |
| `core/constants.py` | FSS 데이터소스 정의, NCR 메트릭 레이블 |

### 데이터 흐름

- **규정검색**: PDF 업로드 → `utils/parser.py` 파싱 → `db.py` 저장 (PDF 파일 자체는 보관 안 함)
- **법령/감독규정**: `api/law_api.py`로 법제처 크롤링 → 조문 텍스트만 DB 저장
- **재무건전성**: `api/fss_api.py` → 금감원 FISIS SF307 → `fss_securities_data` 테이블 (metrics는 JSON 컬럼)

### 레이아웃 구조 (CSS)

- 상단바: `position:fixed; top:8px; left:8px; right:8px; height:68px`
- 사이드바: `position:fixed; top:84px; left:8px; width:70px` (아이콘 전용, 확장 없음)
- stMain: `position:fixed; top:84px; left:86px; right:8px; bottom:0; overflow-y:auto`
- 메인 레이아웃: `st.columns([2.2, 1.1])` (col_main | col_side)
- 보조 패널: `position:sticky; top:0`

모든 CSS는 `app.py`의 단일 `st.markdown("""<style>...""")` 블록에 집중되어 있다.

### 재무건전성 테이블

`views/finance.py`는 `st.dataframe` 대신 `streamlit-aggrid`를 사용한다 (라디오 버튼 충돌 문제 때문). 행 클릭 시 `st.session_state["selected_company"]`에 회사명이 저장되고, 우측 보조 패널에서 스파크라인을 렌더링한다.

### FSS API SSL

금감원 FISIS 서버가 구형 TLS를 사용하므로 `api/fss_api.py`의 `LegacyAdapter`로 SSL 검증을 우회한다 (`CERT_NONE`, `SECLEVEL=1`).

### PDF 미보관 정책

회사 PC의 파일 자동 암호화 정책으로 pdfplumber가 암호화된 파일을 읽지 못한다. 따라서 업로드된 PDF는 파싱 후 즉시 삭제하고 조문 텍스트만 DB에 보관한다.
