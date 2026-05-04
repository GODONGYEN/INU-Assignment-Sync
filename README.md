# INU Assignment Sync

INU LMS 캘린더에서 과제 일정을 수집해 macOS 기본 Calendar 앱에 동기화하는 macOS용 Python 프로젝트입니다.  
CLI와 GUI를 모두 제공하며, 기본값은 `DRY_RUN=true`라서 처음에는 안전하게 테스트할 수 있습니다.  
기본 Python CLI 위에 Electron + React + Tailwind 기반의 macOS 스타일 데스크톱 GUI도 함께 제공합니다.

중요:
- 대상 LMS: [https://cyber.inu.ac.kr](https://cyber.inu.ac.kr)
- 기본 로그인 방식은 수동 로그인입니다.
- CAPTCHA, SSO, 학교 보안장치 우회 기능은 포함하지 않습니다.
- 비밀번호를 코드에 저장하지 않습니다.
- 사용자가 직접 로그인한 세션을 이용하는 방식으로 동작합니다.
- Electron GUI 모드에서는 로그인 완료 후 Enter 입력이 필요 없고, 브라우저 상태를 자동으로 감지합니다.

## 주요 기능

- INU LMS 월간 캘린더에서 여러 달 범위의 과제 이벤트 수집
- 과제 제목, 과목명, 마감 시각 정리
- macOS Calendar 일정 생성 및 수정
- Calendar notes 메타데이터 기반 중복 방지
- SQLite 동기화 기록 저장
- `REMINDER_MINUTES` 기반 다중 알림 설정
- `INCLUDE_PAST_ASSIGNMENTS` 옵션 지원
- `DRY_RUN` 안전 실행 모드 지원
- GUI에서 `.env` 설정 편집 및 실행 가능
- `logs/app.log` 파일에 실행 로그 저장

## 대상 환경

- macOS
- Python 3.10+
- macOS 기본 Calendar 앱
- Playwright Chromium
- Node.js 20+

## 프로젝트 구조

```text
.
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── requirements.txt
├── pyproject.toml
├── main.py
├── app.py
├── setup.sh
├── run_gui.sh
├── run_gui.command
├── electron-app
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── build
│   │   ├── README.md
│   │   ├── entitlements.mac.plist
│   │   └── entitlements.mac.inherit.plist
│   ├── electron
│   │   ├── main.js
│   │   ├── preload.js
│   │   └── notarize.cjs
│   └── scripts
│       ├── build_icon.sh
│       └── generate_icon.swift
│   └── src
│       ├── App.jsx
│       ├── main.jsx
│       └── styles.css
├── src
│   ├── __init__.py
│   ├── config.py
│   ├── scraper.py
│   ├── normalizer.py
│   ├── calendar_sync.py
│   ├── storage.py
│   ├── models.py
│   ├── env_utils.py
│   └── logging_utils.py
├── gui
│   ├── __init__.py
│   └── app_gui.py
├── data
│   └── .gitkeep
├── logs
│   └── .gitkeep
└── docs
    ├── setup.md
    ├── troubleshooting.md
    └── screenshots.md
```

## 설치 방법

가장 쉬운 방법:

```bash
bash setup.sh
```

수동 설치:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## 설정 방법

`.env`에서 주로 확인할 값:

- `BASE_URL=https://cyber.inu.ac.kr`
- `CALENDAR_NAME=INU 과제`
- `CALENDAR_MONTHS_BACK=2`
- `CALENDAR_MONTHS_FORWARD=6`
- `INCLUDE_PAST_ASSIGNMENTS=false`
- `REMINDER_MINUTES=1440,180`
- `DRY_RUN=true`

기본값 설명:

- `CALENDAR_MONTHS_BACK=2`
  현재 달 기준 과거 2개월까지 수집합니다.
- `CALENDAR_MONTHS_FORWARD=6`
  현재 달 기준 미래 6개월까지 수집합니다.
- `INCLUDE_PAST_ASSIGNMENTS=false`
  이미 마감된 과제는 신규 등록하지 않습니다.
- `REMINDER_MINUTES=1440,180`
  마감 1일 전, 3시간 전에 알림을 만듭니다.
- `DRY_RUN=true`
  실제 Calendar를 바꾸지 않고 예정 작업만 로그로 출력합니다.

## CLI 실행 방법

```bash
source .venv/bin/activate
python main.py
```

동작 흐름:

1. 브라우저를 엽니다.
2. 사용자가 직접 LMS에 로그인합니다.
3. 지정한 월 범위의 LMS 캘린더를 순회합니다.
4. 과제 후보를 수집하고 상세 페이지로 보정합니다.
5. Calendar 중복을 검사합니다.
6. 신규 등록 또는 변경된 일정만 반영합니다.
7. 로그를 터미널과 `logs/app.log`에 기록합니다.

CLI 주의:

- `python main.py` 로 실행할 때는 기존처럼 로그인 완료 후 터미널에서 Enter를 눌러 진행합니다.

## GUI 실행 방법

권장 GUI는 Electron 앱입니다.

### Electron GUI 실행

```bash
cd electron-app
npm install
npm run dev
```

개발 모드에서는 Electron DevTools가 자동으로 열립니다.

빌드:

```bash
cd electron-app
npm run build
```

아이콘 생성만 따로 하고 싶다면:

```bash
cd electron-app
npm run build:icon
```

빌드 결과:

- `electron-app/release/` 아래에 `.dmg`, `.zip`, `.app` 관련 산출물이 생성됩니다.
- 인증서가 없으면 로컬 테스트용으로 빌드되고, Apple 자격증명이 있으면 notarization까지 확장할 수 있습니다.
- 앱 아이콘은 `npm run build:icon`으로 다시 생성할 수 있습니다.

Electron GUI 기능:

- 상태 카드
- `.env` 설정 편집
- `동기화 실행` / `DRY RUN 실행`
- SQLite 동기화 기록 초기화
- `logs/app.log` 열기
- Python stdout/stderr 실시간 표시
- 수집/등록/수정/스킵 요약 표시

GUI 로그인 방식:

- Electron GUI에서는 브라우저에서 LMS 로그인을 완료하면 Enter 입력 없이 자동으로 로그인 완료를 감지합니다.
- 로그인 감지 시간은 `.env`의 `LOGIN_WAIT_TIMEOUT_MS`로 조절할 수 있습니다.

### GUI 디버깅 방법

검정 화면이 보일 때는 아래 순서로 확인하세요.

1. `cd electron-app`
2. `npm install`
3. `npm run dev`
4. 자동으로 열린 DevTools의 `Console` 탭 확인
5. 터미널에서 Electron이 출력하는 로드 경로 로그 확인

확인할 항목:

- `http://localhost:5173` 가 실제로 열리는지
- Electron이 dev 모드에서 `loadURL(...)` 을 호출하는지
- preload API가 `window.electronAPI` 또는 `window.inuSync` 로 노출되는지
- `index.html`에 `<div id="root"></div>` 가 있는지
- renderer console에 React runtime error가 있는지
- build 모드라면 `vite.config.js`의 `base: "./"` 설정이 들어 있는지

주의:

- Electron 앱도 내부적으로 기존 `main.py`를 실행합니다.
- `.venv/bin/python`이 있으면 우선 사용하고, 없으면 `python3`를 사용합니다.
- 로그인은 기존과 동일하게 사용자가 브라우저에서 직접 진행합니다.
- `npm run build`는 renderer 빌드 후 Electron Builder로 macOS 배포 파일까지 생성합니다.
- notarization은 Apple 자격증명이 없으면 자동으로 건너뜁니다.

### 레거시 Python GUI 실행

```bash
source .venv/bin/activate
python app.py
```

또는:

```bash
bash run_gui.sh
```

GUI 기능:

- `BASE_URL` 표시
- 캘린더 이름 입력
- 이전/이후 수집 개월 수 설정
- 지난 과제 포함 여부 체크
- `DRY_RUN` 체크
- 알림 시간 입력
- `.env` 자동 저장
- 실행 로그 창
- 상태 표시
- 결과 요약 표시

GUI 버튼:

- `설정 저장`
- `동기화 실행`
- `DRY RUN 실행`
- `동기화 기록 초기화`
- `README 열기`

## DRY_RUN 사용법

처음에는 `DRY_RUN=true` 상태에서 실행하는 것을 권장합니다.

이 모드에서는:

- Calendar에 실제 등록하지 않습니다.
- Calendar에 실제 수정하지 않습니다.
- 예정 작업만 로그로 보여 줍니다.

실제로 Calendar에 반영하려면:

1. GUI에서 `DRY_RUN` 체크를 끕니다.
2. 또는 `.env`에서 `DRY_RUN=false`로 바꿉니다.
3. 다시 실행합니다.

## macOS Calendar 권한 설정

처음 실행할 때 Calendar 접근 권한이 필요할 수 있습니다.

1. 프로그램을 한 번 실행합니다.
2. 권한 팝업이 뜨면 `허용`을 누릅니다.
3. 팝업을 놓쳤다면 다음 경로를 확인합니다.
4. `시스템 설정 > 개인정보 보호 및 보안 > 캘린더`
5. 사용 중인 터미널 앱 또는 Python 실행 앱 권한을 허용합니다.
6. `시스템 설정 > 개인정보 보호 및 보안 > 자동화`도 함께 확인합니다.

권한 문제가 있을 때 나올 수 있는 증상:

- AppleScript 실패
- Calendar 생성 실패
- 기존 이벤트 검색 실패

## 자주 발생하는 오류 해결

### `.env` 없음

- `bash setup.sh`를 다시 실행하세요.
- 또는 `.env.example`을 `.env`로 복사하세요.

### Playwright Chromium 미설치

```bash
playwright install chromium
```

### LMS 로그인 안 됨

- 브라우저에서 실제 로그인까지 완료했는지 확인하세요.
- 로그인 후 월간 캘린더 페이지 접근 상태에서 Enter를 눌러야 합니다.

### 과제가 0개 수집됨

- 캘린더 범위 설정 확인
- selector 설정 확인
- 해당 월에 과제가 실제로 존재하는지 확인

### selector 오류

- `.env`에 저장된 selector가 실제 LMS HTML 구조와 맞는지 확인하세요.

### AppleScript 실패

- Calendar 권한
- Automation 권한
- `DRY_RUN=true` 상태에서 먼저 점검

을 다시 확인하세요.

### SQLite DB 오류

테스트 중 잘못 동기화된 기록 초기화:

```bash
rm -f data/sync_state.sqlite3
```

주의:

- 이 명령은 SQLite 동기화 기록만 지웁니다.
- macOS Calendar 앱에 이미 등록된 일정은 직접 삭제해야 합니다.

## 로그 파일

실행 로그는 자동으로 `logs/app.log`에 저장됩니다.

주의:

- 비밀번호는 저장하지 않습니다.
- 로그인 입력값은 로그에 남기지 않도록 설계했습니다.

## 보안 및 주의사항

- 학교 LMS 약관을 위반하지 않는 범위에서 사용하세요.
- CAPTCHA, SSO, 보안장치 우회 기능은 구현하지 않습니다.
- 개인 계정 정보는 `.env` 또는 코드에 강제로 저장하지 마세요.
- 기본 방식은 수동 로그인 세션 사용입니다.

## 기여 방법

1. 이 저장소를 fork 합니다.
2. 새 브랜치를 만듭니다.
3. 변경 후 테스트합니다.
4. Pull Request를 올립니다.

추가 문서:

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [SECURITY.md](./SECURITY.md)

기여 아이디어:

- selector 자동 진단 개선
- Calendar 이벤트 검색 정밀도 향상
- 더 나은 GUI UX
- 오류 메시지 다국어 지원

## 라이선스

이 프로젝트는 [MIT License](./LICENSE)를 사용합니다.

## GitHub 업로드 방법

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/사용자명/저장소명.git
git push -u origin main
```

업로드 전 체크:

- `.env`가 git에 포함되지 않는지 확인
- `data/*.sqlite3`가 포함되지 않는지 확인
- `logs/*.log`가 포함되지 않는지 확인
- `electron-app/node_modules`, `dist`, `release`가 포함되지 않는지 확인

처음 공개 저장소로 올릴 때 권장 순서:

```bash
git init
git add .
git status
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/사용자명/저장소명.git
git push -u origin main
```

GitHub Actions:

- `.github/workflows/ci.yml`이 포함되어 있어 PR과 `main` 푸시 때 Python 컴파일과 Electron renderer 빌드를 자동 확인합니다.

## Electron 앱 배포 팁

- 기본 빌드 명령:

```bash
cd electron-app
npm run build
```

- 배포 결과물 위치:

```bash
electron-app/release/
```

- 앱 아이콘을 넣고 싶다면:
  `electron-app/build/icon.icns`

- 아이콘을 다시 생성하려면:

```bash
cd electron-app
npm run build:icon
```

- DMG 꾸미기를 하고 싶다면:
  `electron-app/build/background.png`

## macOS 코드 서명 / notarization

정식 배포를 준비하는 유지보수자는 Apple Developer 인증서와 Apple 자격증명이 필요합니다.

지원하는 방식:

- Keychain profile 방식
- Apple ID + app-specific password 방식
- App Store Connect API key 방식

예시 1. Keychain profile 방식

```bash
xcrun notarytool store-credentials "inu-assignment-sync"
  --apple-id "<Apple ID>"
  --team-id "<TEAM_ID>"
  --password "<APP_SPECIFIC_PASSWORD>"

cd electron-app
APPLE_KEYCHAIN_PROFILE=inu-assignment-sync npm run build
```

예시 2. Apple ID 방식

```bash
cd electron-app
APPLE_ID="you@example.com" \
APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx" \
APPLE_TEAM_ID="TEAMID1234" \
npm run build
```

예시 3. App Store Connect API key 방식

```bash
cd electron-app
APPLE_API_KEY="/absolute/path/AuthKey_ABC1234567.p8" \
APPLE_API_KEY_ID="ABC1234567" \
APPLE_API_ISSUER="00000000-0000-0000-0000-000000000000" \
npm run build
```

테스트용으로 notarization만 끄고 싶다면:

```bash
cd electron-app
SKIP_NOTARIZE=true npm run build
```
