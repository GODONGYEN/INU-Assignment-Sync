# INU Assignment Sync

INU LMS 과제 일정을 수집해서 macOS 기본 Calendar 앱에 동기화하는 macOS 데스크톱 앱입니다.

이 앱은 Electron + React GUI 위에서 기존 Python 동기화 엔진을 실행합니다. 사용자는 터미널에서 `npm run dev`를 실행할 필요 없이, 빌드된 `.app`을 더블클릭해서 사용할 수 있습니다.

## 중요한 원칙

- 대상 LMS: [https://cyber.inu.ac.kr](https://cyber.inu.ac.kr)
- 로그인은 사용자가 브라우저에서 직접 진행합니다.
- CAPTCHA, SSO, 학교 보안장치 우회 기능은 없습니다.
- 비밀번호를 코드나 설정 파일에 저장하지 않습니다.
- 처음에는 `DRY_RUN=true`로 테스트하는 것을 권장합니다.

## 앱 설치

GitHub Releases에서 최신 macOS 배포 파일을 내려받을 수 있습니다.

[다운로드 페이지 열기](https://github.com/GODONGYEN/INU-Assignment-Sync/releases)

Apple Silicon Mac은 다음 파일을 권장합니다.

```text
INU Assignment Sync-0.1.0-arm64.dmg
```

설치 방법:

1. `.dmg` 파일을 엽니다.
2. `INU Assignment Sync.app`을 `Applications` 폴더로 옮깁니다.
3. `Applications`에서 앱 아이콘을 더블클릭합니다.

`.zip` 파일을 받은 경우:

1. 압축을 풉니다.
2. `INU Assignment Sync.app`을 더블클릭합니다.

## 처음 설정

앱을 처음 실행하면 사용자 데이터 폴더가 자동으로 만들어집니다.

```text
~/Library/Application Support/INU Assignment Sync/
├── .env
├── data/
├── logs/
├── .venv/
└── ms-playwright/
```

앱 화면에서 설정할 수 있는 값:

- Calendar 이름
- 이전 수집 개월 수
- 이후 수집 개월 수
- 지난 과제 포함 여부
- `DRY_RUN`
- 알림 시간
- 로그인 자동 감지 대기 시간

설정을 바꾼 뒤 `설정 저장`을 누르면 Application Support 폴더의 `.env`에 저장됩니다.

## Python 의존성 준비

앱은 Python 동기화 엔진을 사용합니다. 처음 실행 시 Python 패키지가 준비되지 않았다면 앱 화면에서 안내가 표시됩니다.

앱에서 할 일:

1. `Python 의존성 확인`을 누릅니다.
2. 준비되지 않았다고 나오면 `Python 의존성 설치`를 누릅니다.
3. 앱이 전용 가상환경을 만들고 필요한 패키지와 Playwright Chromium을 설치합니다.

전용 가상환경 위치:

```text
~/Library/Application Support/INU Assignment Sync/.venv/
```

## 동기화 실행

권장 순서:

1. `DRY_RUN`이 켜져 있는지 확인합니다.
2. `설정 저장`을 누릅니다.
3. `DRY RUN 실행`을 누릅니다.
4. 브라우저가 열리면 INU LMS에 직접 로그인합니다.
5. 앱이 로그인 완료를 자동 감지합니다.
6. 로그와 결과 요약을 확인합니다.
7. 문제가 없으면 `DRY_RUN`을 끄고 `동기화 실행`을 누릅니다.

GUI 모드에서는 로그인 완료 후 Enter를 누르지 않습니다.

## Calendar 권한

macOS Calendar 앱에 일정을 등록하려면 권한이 필요할 수 있습니다.

확인 위치:

```text
시스템 설정 > 개인정보 보호 및 보안 > 캘린더
```

필요하면 다음도 확인하세요.

```text
시스템 설정 > 개인정보 보호 및 보안 > 자동화
```

권한 문제가 의심될 때:

- 앱을 다시 실행합니다.
- Calendar 권한을 허용합니다.
- 먼저 `DRY_RUN`으로 테스트합니다.

## 로그 확인

앱 화면에서 `로그 펼치기`를 누르면 실행 로그를 볼 수 있습니다.

로그 파일 위치:

```text
~/Library/Application Support/INU Assignment Sync/logs/app.log
```

앱의 `로그 파일 열기` 버튼으로 바로 열 수 있습니다.

## 동기화 기록 초기화

앱 화면의 `동기화 기록 초기화` 버튼은 SQLite 동기화 기록만 삭제합니다.

삭제되는 파일:

```text
~/Library/Application Support/INU Assignment Sync/data/sync_state.sqlite3
```

주의:

- macOS Calendar 앱에 이미 등록된 일정은 직접 삭제해야 합니다.
- 테스트 중 잘못 등록한 일정은 Calendar 앱에서 확인하세요.

## 문제 해결

### 앱이 Python 의존성 오류를 보여줄 때

- 앱에서 `Python 의존성 설치`를 실행합니다.
- 설치가 실패하면 로그를 펼쳐 상세 오류를 확인합니다.
- macOS에 `python3`가 설치되어 있는지 확인합니다.
- `requirements.txt` 또는 `main.py`를 찾지 못한다는 메시지가 나오면 이전 빌드의 앱일 수 있습니다. 개발자는 `electron-app`에서 `npm run pack` 또는 `npm run dist`로 앱을 다시 만든 뒤 새로 생성된 앱을 실행하세요.
- 설치가 꼬였을 때는 앱을 종료한 뒤 `~/Library/Application Support/INU Assignment Sync/.venv`를 삭제하고 앱에서 `Python 의존성 설치`를 다시 실행할 수 있습니다.

### 로그인 완료가 감지되지 않을 때

- 브라우저에서 INU LMS 로그인이 끝났는지 확인합니다.
- 캘린더 페이지 접근이 가능한지 확인합니다.
- 설정의 로그인 자동 감지 대기 시간을 늘려 봅니다.

### Calendar 등록이 실패할 때

- Calendar 권한을 확인합니다.
- 자동화 권한을 확인합니다.
- `DRY_RUN`으로 먼저 실행해 수집 자체가 되는지 확인합니다.

### 앱이 수정 또는 손상되었다고 나올 때

- 이전에 받은 DMG/ZIP을 삭제하고 GitHub Releases에서 최신 파일을 다시 다운로드하세요.
- 앱을 Applications 폴더로 옮긴 뒤 우클릭해서 `열기`를 선택하세요.
- 그래도 막히면 터미널에서 다음 명령으로 다운로드 격리 속성을 제거한 뒤 다시 실행할 수 있습니다.

```bash
xattr -dr com.apple.quarantine "/Applications/INU Assignment Sync.app"
```

참고: 현재 배포판은 Apple Developer ID로 공증된 앱이 아니므로 처음 실행 시 macOS 보안 확인이 나타날 수 있습니다.

### 과제가 0개 수집될 때

- 수집 개월 범위를 확인합니다.
- 해당 월에 LMS 캘린더 과제가 실제로 있는지 확인합니다.
- INU LMS HTML 구조가 바뀌었다면 selector 수정이 필요할 수 있습니다.

## 개발자용 실행

일반 사용자는 이 섹션을 사용할 필요가 없습니다.

Python CLI:

```bash
bash setup.sh
source .venv/bin/activate
python main.py
```

Electron 개발 서버:

```bash
cd electron-app
npm install
npm run dev
```

개발 모드에서는 DevTools가 자동으로 열립니다.

## 앱 빌드

```bash
cd electron-app
npm install
npm run build
```

빌드 산출물:

```text
electron-app/release/
```

유용한 명령:

```bash
npm run dev
npm run build
npm run pack
npm run dist
npm run open
```

명령 의미:

- `npm run dev`: 개발용 실행
- `npm run build`: 최종 배포 파일 생성
- `npm run pack`: `.app` 폴더만 생성
- `npm run dist`: `.dmg`, `.zip` 생성
- `npm run open`: 빌드된 `.app` 실행

## GitHub 업로드

업로드 전 확인:

- `.env` 제외
- `data/*.sqlite3` 제외
- `logs/*.log` 제외
- `electron-app/node_modules` 제외
- `electron-app/dist` 제외
- `electron-app/release` 제외

처음 업로드:

```bash
git init
git add .
git status
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/사용자명/저장소명.git
git push -u origin main
```

## 기여와 보안

- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [SECURITY.md](./SECURITY.md)

기여 아이디어:

- selector 자동 진단 개선
- Calendar 이벤트 검색 정밀도 향상
- 더 나은 GUI UX
- 오류 메시지 다국어 지원

## 라이선스

이 프로젝트는 [MIT License](./LICENSE)를 사용합니다.
