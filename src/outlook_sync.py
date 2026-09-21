"""Microsoft Graph delegated calendar sync for new Outlook (no COM dependency)."""
import hashlib
import json
import uuid
from datetime import timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from src.config import EVENT_DURATION_MINUTES, REMINDER_MINUTES

GRAPH = 'https://graph.microsoft.com/v1.0'
PROPERTY_ID = 'String {68fb2868-5b27-4e80-934b-86498020dd9e} Name INUAssignmentId'


class GraphError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f'Outlook API 오류 (HTTP {status}). 계정 권한/네트워크를 확인하고 다시 실행하세요.')


class OutlookCalendar:
    def __init__(self, client_id):
        self.client_id = client_id
        self.token = None
        self.calendar_id = None
        self.scope_id = None

    def login(self):
        try:
            uuid.UUID(self.client_id)
        except (ValueError, TypeError, AttributeError):
            raise RuntimeError('Outlook 앱 등록 ID를 설정하세요. README의 Windows 안내를 참고하거나 ICS 내보내기를 선택하세요.') from None
        import msal
        app = msal.PublicClientApplication(self.client_id, authority='https://login.microsoftonline.com/common')
        print('[INFO] Outlook 로그인: 브라우저에서 일정에 사용할 Microsoft 계정을 선택하세요.')
        result = app.acquire_token_interactive(scopes=['Calendars.ReadWrite'], prompt='select_account', timeout=180)
        if 'access_token' not in result:
            raise RuntimeError('Outlook 로그인 실패 또는 취소. 앱 등록과 캘린더 권한 동의를 확인하세요.')
        self.token = result['access_token']
        claims = result.get('id_token_claims', {})
        subject = claims.get('oid') or claims.get('sub')
        if not subject:
            raise RuntimeError('Outlook 계정 식별자를 확인할 수 없습니다.')
        self.scope_id = hashlib.sha256((claims.get('tid', '') + ':' + subject).encode()).hexdigest()
        # Tokens remain in memory for this run only; no passwords/token cache on disk.

    def request(self, method, path, payload=None):
        url = path if path.startswith('https://') else GRAPH + path
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.netloc != 'graph.microsoft.com':
            raise RuntimeError('잘못된 Outlook API 주소입니다.')
        headers = {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json',
                   'Prefer': 'IdType="ImmutableId"'}
        data = json.dumps(payload).encode() if payload is not None else None
        try:
            with urlopen(Request(url, data=data, headers=headers, method=method), timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else {}
        except HTTPError as error:
            # Never log tokens, request headers or raw server bodies.
            raise GraphError(error.code) from None

    def items(self, path):
        while path:
            result = self.request('GET', path)
            yield from result.get('value', [])
            path = result.get('@odata.nextLink')

    def ensure_calendar_exists(self, name):
        self.login()
        matches = [c for c in self.items('/me/calendars?$select=id,name') if c['name'] == name]
        if len(matches) > 1:
            raise RuntimeError('Outlook에 같은 이름의 캘린더가 여러 개 있습니다. 고유한 Calendar 이름을 사용하세요.')
        calendar = matches[0] if matches else self.request('POST', '/me/calendars', {'name': name})
        self.calendar_id = calendar['id']
        self.scope_id = hashlib.sha256((self.scope_id + ':' + self.calendar_id).encode()).hexdigest()

    @property
    def events_path(self):
        return '/me/calendars/' + quote(self.calendar_id, safe='') + '/events'

    def find_existing_calendar_event(self, assignment):
        identity = hashlib.sha256(assignment.external_id.encode()).hexdigest()
        query = urlencode({'$filter': f"singleValueExtendedProperties/Any(ep: ep/id eq '{PROPERTY_ID}' and ep/value eq '{identity}')", '$select': 'id'})
        matches = list(self.items(self.events_path + '?' + query))
        if len(matches) > 1:
            raise RuntimeError('같은 과제의 Outlook 일정이 여러 개입니다. 중복 일정을 확인하세요.')
        return matches[0]['id'] if matches else None

    def payload(self, assignment):
        def value(dt):
            return {'dateTime': dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': 'UTC'}
        identity = hashlib.sha256(assignment.external_id.encode()).hexdigest()
        return {'subject': assignment.event_title, 'body': {'contentType': 'text', 'content': assignment.notes},
                'start': value(assignment.due_at), 'end': value(assignment.due_at + timedelta(minutes=EVENT_DURATION_MINUTES)),
                'isReminderOn': bool(REMINDER_MINUTES), 'reminderMinutesBeforeStart': min(REMINDER_MINUTES) if REMINDER_MINUTES else 0,
                'singleValueExtendedProperties': [{'id': PROPERTY_ID, 'value': identity}]}

    def create_calendar_event(self, assignment):
        payload = self.payload(assignment)
        # Remote identity lookup handles retries across runs; each new creation gets a transaction ID.
        payload['transactionId'] = str(uuid.uuid4())
        return self.request('POST', self.events_path, payload)['id']

    def update_calendar_event(self, uid, assignment):
        try:
            return self.request('PATCH', self.events_path + '/' + quote(uid, safe=''), self.payload(assignment))['id']
        except GraphError as error:
            if error.status == 404:
                return None
            raise
