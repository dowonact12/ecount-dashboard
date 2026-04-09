"""
이카운트 Open API → inventory.json 생성 → git push
실행: python fetch_inventory.py  (또는 run.bat 더블클릭)
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import urllib.request
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
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def get_zone(com_code: str) -> str:
    res = post_json("https://oapi.ecount.com/OAPI/V2/Zone", {"COM_CODE": com_code})
    zone = res.get("Data", {}).get("ZONE")
    if not zone:
        raise RuntimeError(f"ZONE 조회 실패: {res}")
    return zone


def login(zone, com_code, user_id, api_cert_key, lan_type):
    url = f"https://oapi{zone}.ecount.com/OAPI/V2/OAPILogin"
    res = post_json(url, {
        "COM_CODE": com_code,
        "USER_ID": user_id,
        "API_CERT_KEY": api_cert_key,
        "LAN_TYPE": lan_type,
        "ZONE": zone,
    })
    sid = res.get("Data", {}).get("Datas", {}).get("SESSION_ID")
    if not sid:
        raise RuntimeError(f"로그인 실패: {res}")
    return sid


def fetch_product_master(zone, session_id):
    """품목 마스터: 품명, 안전재고, 단위, 분류코드"""
    url = f"https://oapi{zone}.ecount.com/OAPI/V2/InventoryBasic/GetBasicProductsList?SESSION_ID={session_id}"
    res = post_json(url, {"PROD_CD": ""})
    rows = res.get("Data", {}).get("Result", []) or []
    master = {}
    for r in rows:
        pc = r.get("PROD_CD", "")
        master[pc] = {
            "prod_des": r.get("PROD_DES", "") or "",
            "unit": r.get("UNIT", "") or "",
            "safe_qty": float(r.get("SAFE_QTY") or 0),
            "class_cd": r.get("CLASS_CD", "") or "",
        }
    return master


def fetch_inventory_by_location(zone, session_id, base_date):
    """창고별 재고"""
    url = f"https://oapi{zone}.ecount.com/OAPI/V2/InventoryBalance/GetListInventoryBalanceStatusByLocation?SESSION_ID={session_id}"
    res = post_json(url, {"BASE_DATE": base_date})
    return res.get("Data", {}).get("Result", []) or []


def main():
    # 환경변수 우선 (GitHub Actions), 없으면 config.json
    if os.environ.get("ECOUNT_COM_CODE"):
        cfg = {
            "COM_CODE": os.environ["ECOUNT_COM_CODE"],
            "USER_ID": os.environ["ECOUNT_USER_ID"],
            "API_CERT_KEY": os.environ["ECOUNT_API_CERT_KEY"],
            "LAN_TYPE": os.environ.get("ECOUNT_LAN_TYPE", "ko-KR"),
            "ZONE": os.environ.get("ECOUNT_ZONE", ""),
        }
    elif CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        print("[!] config.json 또는 환경변수가 필요합니다.")
        sys.exit(1)

    print("[1/5] ZONE 조회...")
    zone = cfg.get("ZONE") or get_zone(cfg["COM_CODE"])
    print(f"      ZONE={zone}")

    print("[2/5] 로그인...")
    sid = login(zone, cfg["COM_CODE"], cfg["USER_ID"], cfg["API_CERT_KEY"], cfg.get("LAN_TYPE", "ko-KR"))

    print("[3/5] 품목 마스터 조회...")
    master = fetch_product_master(zone, sid)
    print(f"      {len(master)} 품목")

    print("[4/5] 창고별 재고 조회...")
    today = datetime.now().strftime("%Y%m%d")
    rows = fetch_inventory_by_location(zone, sid, today)
    print(f"      {len(rows)} 건")

    items = []
    for r in rows:
        pc = r.get("PROD_CD", "")
        m = master.get(pc, {})
        items.append({
            "prod_cd": pc,
            "prod_des": r.get("PROD_DES") or m.get("prod_des", ""),
            "wh_cd": r.get("WH_CD", "") or "",
            "wh_des": r.get("WH_DES", "") or "",
            "qty": float(r.get("BAL_QTY") or 0),
            "safe_qty": m.get("safe_qty", 0),
            "unit": m.get("unit", ""),
            "class_cd": m.get("class_cd", ""),
            "class_name": m.get("class_cd", ""),  # 분류명 별도 엔드포인트 필요시 추후 확장
        })

    out = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "base_date": today,
        "count": len(items),
        "items": items,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[5/5] 저장: {OUT_PATH}")

    # GitHub Actions 에서는 git push 를 워크플로우가 처리하므로 skip
    if os.environ.get("GITHUB_ACTIONS"):
        return
    try:
        subprocess.run(["git", "add", "docs/inventory.json"], cwd=ROOT, check=True)
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
