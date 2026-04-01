"""
동아쏘시오 포털 자동 로그인
SSO 흐름: business.jsp -> checkserver.jsp -> userLogin 폼 진입 -> selectUserLogin AJAX
비밀번호: SHA256 후 Base64 3중 인코딩한 authKey로 전송
"""

import base64
import hashlib
import json
import re
import urllib.parse

import requests

BASE_URL = "http://dportal.dongasocio.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
}


def login(username: str, password: str) -> requests.Session:
    """로그인 후 인증된 세션 반환"""
    s = requests.Session()
    s.headers.update(HEADERS)

    # 1단계: SSO 초기화
    s.get(f"{BASE_URL}/ekp/sso/business.jsp")

    # 2단계: checkserver.jsp -> ssid 획득
    r2 = s.post(
        f"{BASE_URL}/ekp/sso/checkserver.jsp",
        data={"isToken": "", "secureToken": "", "secureSessionId": "", "mobileYN": "N"},
    )
    ssid_m = re.search(r"name=[\"']ssid[\"'][^>]*value=[\"'](\d+)", r2.text)
    ssid = ssid_m.group(1) if ssid_m else ""

    # 3단계: 로그인 폼 진입 (ssid로 POST) -> currentDate, cmpId 획득
    r3 = s.post(
        f"{BASE_URL}/ekp/view/login/userLogin",
        data={"ssid": ssid, "UserConType": "0"},
    )
    r3.encoding = "utf-8"

    stime = re.search(r'"currentDate":"([^"]+)"', r3.text).group(1)
    cmpid = re.search(r"cmpId\s*:\s*'([^']+)'", r3.text).group(1)

    # 4단계: authKey 생성 (SHA256 + Base64 x3)
    pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    inner = f"{username}|{pw_hash}|{stime}"
    b64 = base64.b64encode
    auth_key = urllib.parse.quote(
        b64(b64(b64(inner.encode()).decode().encode()).decode().encode()).decode()
    )

    # 5단계: selectUserLogin AJAX 호출
    payload = {
        "loginIdType": 1,
        "cmpId": cmpid,
        "deptId": "",
        "langCd": "ko",
        "authKey": auth_key,
        "chkSecurKeyYn": "N",
        "pwdNextChgYn": "N",
        "userConnType": "I",
        "orgLoginPwd": password,
    }
    body = "__REQ_JSON_OBJECT__=" + urllib.parse.quote(
        json.dumps(payload, ensure_ascii=False), safe=""
    )
    s.headers.update({
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/ekp/view/login/userLogin",
    })
    r4 = s.post(
        f"{BASE_URL}/ekp/inc/login/selectUserLogin",
        data=body.encode("utf-8"),
    )
    r4.encoding = "utf-8"

    result = r4.json()
    code = result.get("data", {}).get("loginResultCode", "")
    if code != "loginSuccess":
        raise ValueError(f"로그인 실패: {code}")

    print(f"  로그인 성공 (쿠키 {len(s.cookies)}개)")
    return s


def get_cookie_string(session: requests.Session) -> str:
    return "; ".join(f"{c.name}={c.value}" for c in session.cookies)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    try:
        s = login(os.environ["PORTAL_USERNAME"], os.environ["PORTAL_PASSWORD"])
        print("OK:", get_cookie_string(s)[:80])
    except Exception as e:
        print("ERROR:", e)
