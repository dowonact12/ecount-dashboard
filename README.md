# 이카운트 재고 대시보드

이카운트 ERP의 재고를 실시간으로 확인하는 공개 대시보드.

## 사용법

### 1. 최초 설정
1. `config.sample.json` 을 복사해서 `config.json` 으로 이름 변경
2. 이카운트 Open API 정보 입력:
   - COM_CODE (회사코드)
   - USER_ID (API용 사용자ID)
   - API_CERT_KEY (API 인증키)
   - LAN_TYPE (ko-KR)
   - ZONE (비워두면 자동 조회)

### 2. 수동 실행
`run.bat` 더블클릭 → 이카운트에서 재고 가져와서 GitHub에 푸시

### 3. 자동 실행 (Windows 작업 스케줄러)
- 트리거: 5분마다
- 동작: `run.bat` 실행
- 시작 위치: 이 폴더

### 4. 대시보드 보기
GitHub Pages 링크를 북마크 → 누구나 접속 가능

## 구조
- `fetch_inventory.py` — 이카운트 API 호출
- `config.json` — API 키 (git 제외)
- `docs/` — GitHub Pages 공개 폴더
  - `index.html` / `app.js` / `style.css`
  - `inventory.json` — 스크립트가 갱신
