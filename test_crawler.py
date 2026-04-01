"""크롤러 단독 테스트 - Google Calendar 없이 API 조회만 확인"""
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from login import login
from crawler import CalendarCrawler, CALENDARS

load_dotenv()

KST = timezone(timedelta(hours=9))

print("[1/2] 로그인 중...")
session = login(os.environ["PORTAL_USERNAME"], os.environ["PORTAL_PASSWORD"])

now = datetime.now(KST)
start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
end_dt = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0)

print(f"\n[2/2] 조회 범위: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")

crawler = CalendarCrawler(session=session)
events = crawler.fetch_events(start_dt, end_dt)

cal_names = {c["calendarId"]: c["cldrName"] for c in CALENDARS}
by_cal = {}
for ev in events:
    cal_id = ev.get("calendarId", "unknown")
    by_cal.setdefault(cal_id, []).append(ev)

for cal_id, evs in by_cal.items():
    name = cal_names.get(cal_id, cal_id)
    print(f"\n[{name}] {len(evs)}개")
    for ev in sorted(evs, key=lambda e: e.get("start", ""))[:5]:
        print(f"  {ev.get('start','')[:10]}  {ev.get('title','(제목없음)')}")
    if len(evs) > 5:
        print(f"  ... 외 {len(evs)-5}개")
