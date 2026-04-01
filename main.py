"""
메인 실행 파일
- 실행 시점 기준 당해년도 말까지 일정 동기화
- 예: 2026-04-01 실행 → 2026-04-01 ~ 2026-12-31
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

from crawler import CalendarCrawler
from google_sync import GoogleCalendarSync
from login import login

KST = timezone(timedelta(hours=9))


def main():
    # ── 환경변수 읽기 ──────────────────────────────────────────────
    portal_user = os.environ.get("PORTAL_USERNAME", "").strip()
    portal_pw = os.environ.get("PORTAL_PASSWORD", "").strip()
    if not portal_user or not portal_pw:
        print("[오류] 환경변수 PORTAL_USERNAME, PORTAL_PASSWORD가 없습니다.")
        sys.exit(1)

    sa_json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not sa_json_str:
        print("[오류] 환경변수 GOOGLE_SERVICE_ACCOUNT_JSON이 없습니다.")
        sys.exit(1)

    # 구글 캘린더 ID (탐색생물학2팀, 연구본부장 각각)
    cal_biosearch = os.environ.get("GOOGLE_CAL_BIOSEARCH", "").strip()
    cal_director = os.environ.get("GOOGLE_CAL_DIRECTOR", "").strip()
    if not cal_biosearch or not cal_director:
        print("[오류] 환경변수 GOOGLE_CAL_BIOSEARCH 또는 GOOGLE_CAL_DIRECTOR가 없습니다.")
        sys.exit(1)

    service_account_info = json.loads(sa_json_str)

    # 회사 캘린더 ID → 구글 캘린더 ID 매핑
    calendar_id_map = {
        "SCDM20181031263451722": cal_biosearch,   # [탐색생물학2팀]일정공유
        "SCD16462861591331068345": cal_director,  # 연구본부장 일정
    }

    # ── 날짜 범위: 오늘 ~ 올해 12월 31일 ─────────────────────────
    now = datetime.now(KST)
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0)

    print(f"동기화 범위: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")

    # ── 로그인 ────────────────────────────────────────────────────
    print("\n[1/3] 포털 로그인 중...")
    session = login(portal_user, portal_pw)

    # ── 크롤링 ────────────────────────────────────────────────────
    print("\n[2/3] 회사 캘린더 크롤링 중...")
    crawler = CalendarCrawler(session=session)
    events = crawler.fetch_events(start_dt, end_dt)

    if not events:
        print("  일정이 없거나 인증이 만료되었습니다. 쿠키를 확인하세요.")
        sys.exit(1)

    # ── 구글 캘린더 동기화 ────────────────────────────────────────
    print("\n[3/3] Google Calendar 동기화 중...")
    syncer = GoogleCalendarSync(service_account_info, calendar_id_map)
    syncer.sync(events, start_dt, end_dt)

    print("\n✓ 동기화 완료")


if __name__ == "__main__":
    main()
