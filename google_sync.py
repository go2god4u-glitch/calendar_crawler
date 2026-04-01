"""
Google Calendar 동기화
- 인증: 서비스 계정 (Service Account)
- 전략: companyEventId를 extendedProperty로 추적하여 생성/수정/삭제 동기화
"""

import json
from datetime import datetime, timezone, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

KST = timezone(timedelta(hours=9))
SCOPES = ["https://www.googleapis.com/auth/calendar"]
SYNC_TAG = "dportal_crawler"

# 회사 캘린더 ID → 구글 캘린더 ID 매핑 (main.py에서 환경변수로 주입)
# SCDM20181031263451722  → GOOGLE_CAL_BIOSEARCH
# SCD16462861591331068345 → GOOGLE_CAL_DIRECTOR


class GoogleCalendarSync:
    def __init__(self, service_account_info: dict, calendar_id_map: dict):
        """
        calendar_id_map: {"회사캘린더ID": "구글캘린더ID", ...}
        """
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        self.service = build("calendar", "v3", credentials=creds)
        self.cal_id_map = calendar_id_map

    def sync(self, company_events: list, start_dt: datetime, end_dt: datetime):
        """회사 일정 목록을 구글 캘린더에 동기화"""
        # 회사 캘린더별로 그룹화
        by_cal: dict[str, list] = {}
        for ev in company_events:
            cal_id = ev.get("calendarId", "")
            by_cal.setdefault(cal_id, []).append(ev)

        for company_cal_id, events in by_cal.items():
            google_cal_id = self.cal_id_map.get(company_cal_id)
            if not google_cal_id:
                print(f"  [스킵] 매핑 없음: {company_cal_id}")
                continue
            cal_name = events[0].get("cldrName") or company_cal_id
            print(f"\n[{cal_name}] 동기화 시작 ({len(events)}개)")
            self._sync_calendar(google_cal_id, events, start_dt, end_dt)

    def _sync_calendar(
        self,
        google_cal_id: str,
        company_events: list,
        start_dt: datetime,
        end_dt: datetime,
    ):
        # 구글 캘린더에서 기존 동기화 이벤트 조회
        existing = self._get_synced_events(google_cal_id, start_dt, end_dt)
        existing_map = {
            ev["extendedProperties"]["private"]["companyEventId"]: ev
            for ev in existing
        }

        company_map = {ev["id"]: ev for ev in company_events if ev.get("id")}

        created = updated = deleted = 0

        # 생성 또는 수정
        for company_id, ev in company_map.items():
            google_event = self._build_google_event(ev)
            if company_id in existing_map:
                existing_ev = existing_map[company_id]
                if self._needs_update(existing_ev, google_event):
                    self.service.events().update(
                        calendarId=google_cal_id,
                        eventId=existing_ev["id"],
                        body=google_event,
                    ).execute()
                    updated += 1
            else:
                self.service.events().insert(
                    calendarId=google_cal_id, body=google_event
                ).execute()
                created += 1

        # 회사 캘린더에서 삭제된 이벤트 제거
        for company_id, google_ev in existing_map.items():
            if company_id not in company_map:
                self.service.events().delete(
                    calendarId=google_cal_id, eventId=google_ev["id"]
                ).execute()
                deleted += 1

        print(f"  생성 {created} / 수정 {updated} / 삭제 {deleted}")

    def _get_synced_events(
        self, google_cal_id: str, start_dt: datetime, end_dt: datetime
    ) -> list:
        """이 스크립트가 동기화한 이벤트만 조회"""
        result = []
        page_token = None
        while True:
            resp = (
                self.service.events()
                .list(
                    calendarId=google_cal_id,
                    timeMin=start_dt.isoformat(),
                    timeMax=end_dt.isoformat(),
                    privateExtendedProperty=f"syncedBy={SYNC_TAG}",
                    pageToken=page_token,
                    singleEvents=True,
                    maxResults=2500,
                )
                .execute()
            )
            result.extend(resp.get("items", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return result

    def _build_google_event(self, ev: dict) -> dict:
        """회사 일정 → 구글 캘린더 이벤트 변환"""
        all_day = ev.get("allDay") == "Y"

        if all_day:
            start = {"date": ev["start"][:10]}
            # 종일 이벤트는 end가 exclusive이므로 하루 더
            end_date = datetime.strptime(ev["end"][:10], "%Y-%m-%d") + timedelta(days=1)
            end = {"date": end_date.strftime("%Y-%m-%d")}
        else:
            start_dt = datetime.strptime(ev["start"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=KST
            )
            end_dt = datetime.strptime(ev["end"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=KST
            )
            start = {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Seoul"}
            end = {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Seoul"}

        return {
            "summary": ev.get("title") or "(제목 없음)",
            "start": start,
            "end": end,
            "extendedProperties": {
                "private": {
                    "companyEventId": ev["id"],
                    "syncedBy": SYNC_TAG,
                }
            },
        }

    def _needs_update(self, existing_ev: dict, new_ev: dict) -> bool:
        """제목, 시작/종료 시간이 다르면 업데이트 필요"""
        if existing_ev.get("summary") != new_ev.get("summary"):
            return True
        if existing_ev.get("start") != new_ev.get("start"):
            return True
        if existing_ev.get("end") != new_ev.get("end"):
            return True
        return False
