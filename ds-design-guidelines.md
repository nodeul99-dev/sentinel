# DS투자증권 사내 웹페이지 디자인 가이드라인
> DS Asset 그룹 웹사이트(dsasset.co.kr) 디자인 언어 기반 · 사내 시스템용 파생 가이드

---

## 1. 브랜드 색상 분석 (DS Asset 기반)

DS Asset 메인 사이트를 분석한 결과, 다음과 같은 디자인 언어를 확인했습니다.

- **기조**: 고급스러운 절제미 (Refined Minimalism)
- **배경**: 순백(#FFFFFF) + 오프화이트 계열
- **텍스트**: 짙은 차콜(거의 블랙)
- **포인트 컬러**: 웜 베이지/샌드, 골드 계열 (일러스트 내 금화, 앤빌 색조)
- **강조**: 아주 얇은 검정 라인, 소문자 타이포그래피

---

## 2. 사내 시스템 색상 팔레트

DS Asset의 정제된 품격을 유지하면서, 사내 대시보드/업무 시스템에 적합하도록 조정한 팔레트입니다.

### CSS Variables (복사해서 바로 사용)

```css
:root {
  /* === Brand Core === */
  --color-primary:        #1A1A1A;   /* DS 시그니처 차콜 블랙 (헤더, 강조 텍스트) */
  --color-secondary:      #C8A96E;   /* 골드 베이지 (포인트, 버튼 accent) */
  --color-secondary-dark: #A8894E;   /* 골드 다크 (hover 상태) */

  /* === Background === */
  --bg-base:              #FFFFFF;   /* 메인 배경 */
  --bg-subtle:            #F7F5F2;   /* 카드, 사이드바 배경 (오프화이트) */
  --bg-muted:             #EDE9E3;   /* 테이블 짝수행, 구분선 배경 */
  --bg-overlay:           #FAF8F5;   /* 모달, 팝업 배경 */

  /* === Text === */
  --text-primary:         #1A1A1A;   /* 본문 주요 텍스트 */
  --text-secondary:       #5A5A5A;   /* 보조 텍스트, 레이블 */
  --text-muted:           #9A9690;   /* 비활성, 힌트 텍스트 */
  --text-inverse:         #FFFFFF;   /* 다크 배경 위 텍스트 */

  /* === Border === */
  --border-light:         #E8E4DE;   /* 카드 테두리, 구분선 */
  --border-medium:        #C8C2B8;   /* 강조 구분선 */
  --border-strong:        #1A1A1A;   /* 헤더 하단선, 포인트 라인 */

  /* === Status Colors (사내 시스템용) === */
  --status-positive:      #4A7C59;   /* 상승, 승인, 정상 (그린 → 차분한 톤) */
  --status-negative:      #8B3A3A;   /* 하락, 반려, 경고 (레드 → 차분한 톤) */
  --status-warning:       #B87333;   /* 주의, 검토중 (코퍼 톤) */
  --status-info:          #3A5F8B;   /* 정보, 진행중 (네이비 블루) */
  --status-neutral:       #6A6A6A;   /* 중립, 미처리 */

  /* === Interactive === */
  --btn-primary-bg:       #1A1A1A;
  --btn-primary-text:     #FFFFFF;
  --btn-primary-hover:    #333333;
  --btn-secondary-bg:     transparent;
  --btn-secondary-border: #1A1A1A;
  --btn-secondary-text:   #1A1A1A;
  --btn-accent-bg:        #C8A96E;   /* 골드 CTA 버튼 */
  --btn-accent-text:      #FFFFFF;

  /* === Shadow === */
  --shadow-sm:  0 1px 3px rgba(26,26,26,0.06);
  --shadow-md:  0 4px 12px rgba(26,26,26,0.08);
  --shadow-lg:  0 8px 24px rgba(26,26,26,0.10);
}
```

---

## 3. 타이포그래피

DS Asset이 사용하는 세리프+산세리프 대비 기반의 고급스러운 조합을 따릅니다.

```css
/* 한국어 폰트 스택 */
--font-display:  'Noto Serif KR', 'Apple SD Gothic Neo', serif;   /* 제목, 강조 */
--font-body:     'Pretendard', 'Apple SD Gothic Neo', sans-serif;  /* 본문, UI */
--font-mono:     'JetBrains Mono', 'D2Coding', monospace;          /* 수치, 코드 */

/* 폰트 사이즈 스케일 */
--text-xs:    0.75rem;   /* 12px - 태그, 배지 */
--text-sm:    0.875rem;  /* 14px - 보조 텍스트 */
--text-base:  1rem;      /* 16px - 본문 */
--text-lg:    1.125rem;  /* 18px - 강조 본문 */
--text-xl:    1.25rem;   /* 20px - 소제목 */
--text-2xl:   1.5rem;    /* 24px - 제목 */
--text-3xl:   2rem;      /* 32px - 페이지 타이틀 */
```

---

## 4. 컴포넌트별 적용 지침

### 헤더 / 네비게이션
- 배경: `--bg-base` (white)
- 하단 보더: `1px solid --border-strong` (검정 라인 - DS Asset 시그니처)
- 로고/메뉴: `--text-primary`
- 활성 메뉴: `--color-secondary` (골드 언더라인)

### 사이드바 (사내 시스템)
- 배경: `--color-primary` (#1A1A1A) 또는 `--bg-subtle`
- 다크 사이드바의 텍스트: `--text-inverse`
- 활성 항목: `--color-secondary` 좌측 보더 + 배경 약간 밝게

### 카드 / 패널
- 배경: `--bg-base` 또는 `--bg-subtle`
- 테두리: `1px solid --border-light`
- 그림자: `--shadow-sm` (과도한 그림자 지양)

### 데이터 테이블 (NCR, 리스크 대시보드 등)
- 헤더행: `--bg-muted` + `--text-primary` bold
- 홀수행: `--bg-base`
- 짝수행: `--bg-subtle`
- 수치 양수: `--status-positive`
- 수치 음수: `--status-negative`
- 수치 경보: `--status-warning`
- 폰트: `--font-mono` (정렬 일관성)

### 버튼
| 용도 | 배경 | 텍스트 |
|------|------|--------|
| 주요 액션 | `--btn-primary-bg` | `--btn-primary-text` |
| 보조 액션 | transparent + border | `--btn-secondary-text` |
| 승인/확정 | `--btn-accent-bg` (골드) | white |
| 위험 액션 | `--status-negative` | white |

---

## 5. 다크모드 고려사항

사내 대시보드는 장시간 사용하므로 다크모드 지원을 권장합니다.

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg-base:      #111111;
    --bg-subtle:    #1C1C1C;
    --bg-muted:     #242424;
    --text-primary: #F0EDE8;
    --text-secondary:#B0ACA6;
    --border-light: #2E2E2E;
    --border-medium:#3E3A34;
    /* color-secondary (골드)는 다크에서도 잘 어울림 - 유지 */
  }
}
```

---

## 6. Claude Code 사용 지침

이 파일을 Claude Code에 적용할 때는 다음 프롬프트를 추가하세요.

```
이 프로젝트는 ds-design-guidelines.md의 디자인 시스템을 따릅니다.
- CSS variables는 :root에 반드시 선언하고 하드코딩 색상값 사용 금지
- DS Asset 그룹의 정제된 미니멀리즘 기조 유지
- 골드 계열(--color-secondary)은 포인트에만 절제해서 사용
- 상태 색상(status-*)은 금융 데이터 표시에 일관되게 적용
- 폰트는 Pretendard 또는 Noto Serif KR 사용
```

---

## 7. 금지 사항

Claude Code로 웹페이지 생성 시 아래를 명시적으로 금지하면 품질이 올라갑니다.

- ❌ 보라색/파란색 그라데이션 배경
- ❌ Inter, Roboto 등 일반적 폰트
- ❌ 과도한 그림자, 둥근 모서리 남발
- ❌ 네온 컬러, 형광 accent
- ❌ 밝은 원색 버튼 (빨강, 초록 원색)
- ✅ 대신: 차콜+골드+오프화이트의 절제된 조합 유지

---

*작성 기준: DS Asset (dsasset.co.kr) 웹사이트 디자인 분석 · 2026.02*
*DS투자증권 리스크관리실 내부 사용*
