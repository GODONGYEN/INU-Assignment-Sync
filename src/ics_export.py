"""Portable calendar snapshot. Importing this file is not automatic sync."""
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path


def escape(value):
    return value.replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def fold(line):
    parts, current = [], ''
    for char in line:
        if len((current + char).encode('utf-8')) > 75:
            parts.append(current)
            current = ' '
        current += char
    return '\r\n'.join(parts + [current])


def export_calendar(assignments, path, calendar_name, duration, reminders):
    def utc(value):
        return value.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//INU Assignment Sync//Calendar//KO',
             'CALSCALE:GREGORIAN', 'X-WR-CALNAME:' + escape(calendar_name)]
    for item in assignments:
        uid = hashlib.sha256(item.external_id.encode()).hexdigest() + '@inu-assignment-sync'
        lines += ['BEGIN:VEVENT', 'UID:' + uid, 'DTSTAMP:' + utc(datetime.now(timezone.utc)),
                  'DTSTART:' + utc(item.due_at), 'DTEND:' + utc(item.due_at + timedelta(minutes=duration)),
                  'SUMMARY:' + escape(item.event_title), 'DESCRIPTION:' + escape(item.notes),
                  'URL:' + escape(item.link)]
        for minutes in reminders:
            lines += ['BEGIN:VALARM', f'TRIGGER:-PT{int(minutes)}M', 'ACTION:DISPLAY',
                      'DESCRIPTION:' + escape(item.event_title), 'END:VALARM']
        lines.append('END:VEVENT')
    lines.append('END:VCALENDAR')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_bytes(('\r\n'.join(map(fold, lines)) + '\r\n').encode('utf-8'))
    temp.replace(path)
    return path
