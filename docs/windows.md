# Windows 사용 안내

Windows 10/11 x64용 Electron 설치 프로그램을 제공합니다. 새 Outlook은 Microsoft Graph로 연동하며, 클래식 Outlook/COM이나 유료 Office 설치가 필요하지 않습니다. Microsoft 계정에 Outlook.com 또는 Exchange Online 캘린더가 있어야 합니다. Outlook에 연결된 Gmail 캘린더를 Graph로 수정하는 기능은 지원하지 않습니다.

## 설치

GitHub Releases의 `INU-Assignment-Sync-0.2.0-windows-x64.exe`를 실행합니다. 개발 빌드는 저장소 Actions → Windows installer → 성공한 실행의 Artifacts에서도 받을 수 있습니다. Windows 설치 파일은 코드 서명되지 않았습니다.

Python 3.11 런타임이 포함됩니다. 앱에서 **Python 의존성 설치**를 실행하면 사용자 폴더에 전용 가상환경과 Chromium을 준비합니다. 이 단계에는 인터넷이 필요합니다. 데이터와 설정은 `%APPDATA%\INU Assignment Sync`에 저장됩니다.

## 선택 1: Outlook 자동 동기화

배포자 또는 사용자가 Microsoft Entra에 데스크톱 앱을 한 번 등록해야 합니다. 현재 배포본에는 공용 앱 등록 ID가 포함되어 있지 않습니다. 앱 등록을 할 수 없다면 아래 ICS 방식을 사용하세요.

1. [Microsoft Entra 관리 센터](https://entra.microsoft.com/)의 앱 등록에서 새 앱을 만듭니다.
2. 지원 계정 유형은 **모든 조직 디렉터리의 계정 및 개인 Microsoft 계정**을 선택합니다.
3. 인증 → 플랫폼 추가 → **모바일 및 데스크톱 애플리케이션**에서 리디렉션 URI `http://localhost`를 추가합니다.
4. Microsoft Graph의 **위임된 권한** `Calendars.ReadWrite`를 추가합니다. 앱 비밀(Client Secret)은 만들거나 입력하지 않습니다.
5. Application (client) ID를 앱 설정의 **Outlook 앱 등록 ID**에 입력하고 저장합니다.
6. DRY RUN으로 LMS 수집을 확인합니다. DRY RUN은 Outlook에 로그인하거나 일정을 변경하지 않으므로 신규/수정 구분은 로컬 미리보기입니다.
7. 실제 동기화를 실행하면 LMS 로그인 후 Microsoft 계정 선택 창이 열립니다. 동기화할 Outlook 계정으로 로그인하고 캘린더 권한을 허용합니다.

학교/회사 계정은 조직 정책에 따라 관리자 승인이 필요할 수 있습니다. 앱은 비밀번호나 토큰을 파일에 저장하지 않으며 실제 동기화마다 Microsoft 로그인을 진행합니다.

같은 이름의 캘린더가 없으면 생성합니다. 계정·캘린더별 기록을 분리하고, 과제 식별자를 Outlook 일정 속성에 저장해 재실행과 마감 변경 시 중복을 방지합니다. 수집 범위에서 사라진 과제를 자동 삭제하지 않습니다. Outlook 알림은 설정한 값 중 마감에 가장 가까운 한 개를 사용합니다(예: `1440,180` → 180분 전).

참고: [데스크톱 앱 등록](https://learn.microsoft.com/en-us/entra/identity-platform/scenario-desktop-app-configuration), [일정 생성 권한](https://learn.microsoft.com/en-us/graph/api/calendar-post-events?view=graph-rest-1.0).

## 선택 2: ICS 파일 내보내기

앱 등록이나 Microsoft 로그인 없이 사용할 수 있습니다.

1. 캘린더 연결 방식에서 **ICS 파일 내보내기**를 선택합니다.
2. DRY RUN을 끄고 실행하면 `data\inu-assignments.ics`가 생성됩니다.
3. **내보낸 파일 폴더 열기**로 파일을 찾습니다.
4. 새 Outlook 또는 Outlook 웹의 일정 → 일정 추가 → 파일에서 업로드로 가져옵니다.

ICS는 현재 과제의 스냅샷입니다. 마감일 변경이 자동 반영되지 않고, 반복 가져오기는 중복을 만들 수 있습니다. 반복 사용에는 전용 가져오기 캘린더를 관리하거나 Outlook 자동 동기화를 사용하세요. DRY RUN은 파일을 생성하지 않습니다.

[Microsoft 가져오기 안내](https://support.microsoft.com/en-us/outlook/import-or-subscribe-to-a-calendar-in-outlook-com-or-outlook-on-the-web)

## 개발 및 검증

Windows에서 Python 3.11과 Node.js 20을 준비한 뒤 프로젝트 루트에서 실행합니다.

```powershell
python -m pip install -r requirements.txt
python scripts/bundle_windows_python.py
cd electron-app
npm ci
npm run dist:win
```

GitHub Actions가 Windows에서 파서/Graph 모의 테스트, 플랫폼 경로 테스트, 설치 파일 빌드 및 포함된 Python의 실행을 확인합니다. 실제 Microsoft 계정 로그인·일정 생성과 Windows 설치 마법사 전체 흐름은 별도 사용자 검증이 필요합니다.
