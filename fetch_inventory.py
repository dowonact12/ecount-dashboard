"""
이카운트 Open API → inventory.json 생성 → git push
실행: python fetch_inventory.py  (또는 run.bat 더블클릭)
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.parse
import ssl

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.json"
OUT_PATH = ROOT / "docs" / "inventory.json"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def get_zone(com_code: str) -> str:
    """회사코드로 ZONE 조회"""
    url = "https://oapi.ecount.com/OAPI/V2/Zone"
    res = post_json(url, {"COM_CODE": com_code})
    zone = res.get("Data", {}).get("ZONE")
    if not zone:
        raise RuntimeError(f"ZONE 조회 실패: {res}")
    return zone


def login(zone: str, com_code: str, user_id: str, api_cert_key: str, lan_type: str) -> str:
    """로그인하여 SESSION_ID 획득"""
    url = f"https://oapi{zone}.ecount.com/OAPI/V2/OAPILogin"
    payload = {
        "COM_CODE": com_code,
        "USER_ID": user_id,
        "API_CERT_KEY": api_cert_key,
        "LAN_TYPE": lan_type,
        "ZONE": zone,
    }
    res = post_json(url, payload)
    datas = res.get("Data", {}).get("Datas", {})
    session_id = datas.get("SESSION_ID")
    if not session_id:
        raise RuntimeError(f"로그인 실패: {res}")
    return session_id


def fetch_inventory(zone: str, session_id: str, base_date: str) -> list:
    """재고 현황 조회 (품목/창고별 현재고)"""
    url = f"https://oapi{zone}.ecount.com/OAPI/V2/InventoryBalance/GetListInventoryBalanceStatus?SESSION_ID={session_id}"
    payload = {
        "BASE_DATE": base_date,  # YYYYMMDD
    }
    res = post_json(url, payload)
    result = res.get("Data", {}).get("Result", [])
    return result


def main():
    if not CONFIG_PATH.exists():
        print("[!] config.json 이 없습니다. config.sample.json 을 복사해서 값을 채워주세요.")
        sys.exit(1)

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    com_code = cfg["COM_CODE"]
    user_id = cfg["USER_ID"]
    api_cert_key = cfg["API_CERT_KEY"]
    lan_type = cfg.get("LAN_TYPE", "ko-KR")

    print("[1/4] ZONE 조회...")
    zone = cfg.get("ZONE") or get_zone(com_code)
    print(f"      ZONE={zone}")

    print("[2/4] 로그인...")
    session_id = login(zone, com_code, user_id, api_cert_key, lan_type)
    print("      SESSION_ID 획득")

    print("[3/4] 재고 조회...")
    today = datetime.now().strftime("%Y%m%d")
    rows = fetch_inventory(zone, session_id, today)
    print(f"      {len(rows)} 건")

    # 정규화: 대시보드가 쓰기 쉬운 형태로
    items = []
    for r in rows:
        items.append({
            "prod_cd": r.get("PROD_CD", ""),
            "prod_des": r.get("PROD_DES", ""),
            "wh_cd": r.get("WH_CD", ""),
            "wh_des": r.get("WH_DES", ""),
            "qty": float(r.get("BAL_QTY") or 0),
            "safe_qty": float(r.get("SAFE_QTY") or 0),
            "unit": r.get("BASE_UNIT", ""),
            "class_cd": r.get("CLASS_CD", ""),
            "class_name": r.get("CLASS_NAME", ""),
        })

    out = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "base_date": today,
        "count": len(items),
        "items": items,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[4/4] 저장: {OUT_PATH}")

    # git push
    try:
        subprocess.run(["git", "add", "docs/inventory.json"], cwd=ROOT, check=True)
        # 변경 없으면 commit 실패 → 무시
        r = subprocess.run(
            ["git", "commit", "-m", f"update inventory {out['updated_at']}"],
            cwd=ROOT,
        )
        if r.returncode == 0:
            subprocess.run(["git", "push"], cwd=ROOT, check=True)
            print("      git push 완료")
        else:
            print("      변경 없음 (skip)")
    except Exception as e:
        print(f"      git push 실패: {e}")


if __name__ == "__main__":
    main()
