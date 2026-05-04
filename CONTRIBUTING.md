# Contributing

INU Assignment Sync에 기여해 주셔서 감사합니다.

## 개발 전 확인

- macOS 환경을 권장합니다.
- Python 3.10+
- Node.js 20+
- INU LMS 로그인은 반드시 수동 로그인 기준을 유지합니다.
- CAPTCHA, SSO, 보안장치 우회 코드는 추가하지 않습니다.
- 비밀번호, 쿠키, 개인 토큰을 코드나 문서에 저장하지 않습니다.

## 기본 개발 흐름

```bash
bash setup.sh
cd electron-app
npm install
```

CLI 확인:

```bash
source .venv/bin/activate
python main.py
```

Electron renderer 확인:

```bash
cd electron-app
npm run dev
```

## Pull Request 가이드

- 변경 목적이 분명한 작은 PR을 선호합니다.
- UI 변경이면 스크린샷을 함께 남겨 주세요.
- selector 변경이면 어떤 LMS HTML 구조를 기준으로 했는지 설명해 주세요.
- Calendar 연동 로직을 바꿀 때는 중복 등록, 업데이트, DRY_RUN 동작을 함께 점검해 주세요.

## 커밋 전 체크

Python:

```bash
python3 -m compileall main.py src gui
```

Electron:

```bash
cd electron-app
npm run build:renderer
```

## 금지 사항

- `.env` 커밋 금지
- `data/*.sqlite3` 커밋 금지
- `logs/*.log` 커밋 금지
- `electron-app/node_modules`, `dist`, `release` 커밋 금지

## 이슈 리포트 팁

다음 정보를 함께 적어 주시면 원인 파악이 빨라집니다.

- macOS 버전
- Python 버전
- Node.js 버전
- `npm run dev` 또는 `python main.py` 실행 방식
- DevTools Console 오류
- `logs/app.log` 일부
