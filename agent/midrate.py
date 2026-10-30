"""시장 환율(중간값) 수집. 업체 환율의 숨은 마진을 재는 기준이다.

1순위 open.er-api.com, 2순위 fawazahmed0 currency-api(jsDelivr), 3순위 우즈베키스탄 중앙은행.
모두 키가 필요 없다.
"""
import requests

UA = {"User-Agent": "Mozilla/5.0 (remit-compare student project)"}


def _er_api():
    # USD 기준으로 받아야 소수 자릿수가 충분하다
    d = requests.get("https://open.er-api.com/v6/latest/USD", headers=UA, timeout=15).json()
    krw, uzs = d["rates"]["KRW"], d["rates"]["UZS"]
    return {"uzs_per_krw": uzs / krw, "usd_per_krw": 1 / krw,
            "source": "open.er-api.com", "updated": d["time_last_update_utc"]}


def _fawaz():
    url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/krw.json"
    d = requests.get(url, headers=UA, timeout=15).json()
    return {"uzs_per_krw": d["krw"]["uzs"], "usd_per_krw": d["krw"]["usd"],
            "source": "fawazahmed0 currency-api", "updated": d["date"]}


def _cbu():
    d = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/", headers=UA, timeout=10).json()
    rate = {x["Ccy"]: float(x["Rate"]) / float(x.get("Nominal", 1)) for x in d}
    return {"uzs_per_krw": rate["KRW"], "usd_per_krw": rate["KRW"] / rate["USD"],
            "source": "cbu.uz", "updated": d[0]["Date"]}


def get_mid_rate() -> dict:
    errors = []
    for fn in (_er_api, _fawaz, _cbu):
        try:
            return fn()
        except Exception as e:  # 다음 출처로 넘어간다
            errors.append(f"{fn.__name__}: {e}")
    raise RuntimeError("시장 환율을 하나도 받지 못함: " + " / ".join(errors))
