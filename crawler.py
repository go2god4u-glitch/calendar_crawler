"""
동아쏘시오 포털 캘린더 크롤러
- 인증: 브라우저 쿠키 사용
- API: /ekp/service/schedule/sche/selectScheduleListArray (POST)
- 대상: [탐색생물학2팀]일정공유, 연구본부장 일정
"""

import json
import urllib.parse
from datetime import datetime, timezone, timedelta

import requests

BASE_URL = "http://dportal.dongasocio.com"
KST = timezone(timedelta(hours=9))

# 크롤링 대상 캘린더
CALENDARS = [
    {
        "calendarId": "SCDM20181031263451722",
        "cldrName": "[탐색생물학2팀]일정공유",
        "type": "100",
        "bassCldrYn": "Y",
        "shareYn": "Y",
        "useAuth": 1,
        "bgColor": "#ffad46",
        "fgColor": "#000000",
        "sortNum": "12",
        "ownEmpId": "M655732400",
        "cldr_name": "[탐색생물학2팀]일정공유",
    },
    {
        "calendarId": "SCD16462861591331068345",
        "cldrName": "연구본부장 일정",
        "type": "100",
        "bassCldrYn": "N",
        "shareYn": "Y",
        "useAuth": 1,
        "bgColor": "#42d692",
        "fgColor": "#000000",
        "sortNum": "13",
        "ownEmpId": "M183503848",
        "cldr_name": "연구본부장 일정",
    },
]


class CalendarCrawler:
    def __init__(self, session: requests.Session):
        """login.py의 login()이 반환한 인증된 세션을 받아서 사용"""
        self.session = session
        self.session.headers.update(
            {
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": f"{BASE_URL}/ekp/main/home/homGwMainSub?gMenuId=schedule",
                "Origin": BASE_URL,
            }
        )

    def fetch_events(self, start_dt: datetime, end_dt: datetime) -> list:
        """지정 기간의 일정 목록 조회 (두 캘린더 합산)"""
        payload = {
            "scheduleParamList": CALENDARS,
            "searChStDateTime": int(start_dt.timestamp()),
            "searChEndDateTime": int(end_dt.timestamp()),
        }
        body = "__REQ_JSON_OBJECT__=" + urllib.parse.quote(
            json.dumps(payload, ensure_ascii=False), safe=""
        )

        resp = self.session.post(
            f"{BASE_URL}/ekp/service/schedule/sche/selectScheduleListArray",
            data=body.encode("utf-8"),
        )
        resp.raise_for_status()

        data = resp.json()
        events = data if isinstance(data, list) else []
        print(f"  조회된 일정 수: {len(events)}개")
        return events
