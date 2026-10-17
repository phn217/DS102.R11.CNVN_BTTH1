import random
import re
import time
from urllib.parse import urljoin
import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://bonbanh.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0", "Accept-Language": "vi-VN,vi;q=0.9"}
BRANDS = ["toyota", "hyundai", "kia", "mazda", "ford", "honda", "mitsubishi", "vinfast", "mercedes_benz", "bmw", 
          "lexus", "audi", "suzuki", "nissan", "chevrolet", "peugeot", "volkswagen", "isuzu", "mg", "landrover", 
          "porsche", "volvo", "subaru", "mini", "jeep", "daewoo", "byd", "jaguar", "bentley", "rolls_royce",
          "ferrari", "lamborghini", "maserati", "aston_martin", "mekong", "vinaxuki", "tobe", "triumph"]
MAX_PAGES = 30
DELAY = 1.0 

ITEM_URL = re.compile(r"^https://bonbanh\.com/xe-[^/?#]+-(\d{5,9})$") 
dung_trinh_duyet = False 
_pw = {}

def tim(pattern, text):
    #tìm mẫu đầu tiên trong chuỗi, không thấy thì trả về None
    m = re.search(pattern, text or "", re.I)
    return m.group(1).strip() if m else None

def sang_trieu(s):
    if not s:
        return None
    ty = re.search(r"(\d+(?:[.,]\d+)?)\s*Tỷ", s, re.I)
    tr = re.search(r"(\d+(?:[.,]\d+)?)\s*Triệu", s, re.I)
    if not ty and not tr:
        return None
    f = lambda x: float(x.replace(",", "."))
    return (f(ty.group(1)) * 1000 if ty else 0) + (f(tr.group(1)) if tr else 0)

def tai_trang(url):
    global dung_trinh_duyet
    if not dung_trinh_duyet:
        try:
            html = requests.get(url, headers=HEADERS, timeout=30).text
        except Exception as e:
            print("  Lỗi mạng:", e)
            return ""
        if "Tổng:" in html: 
            return html
        print("  requests không nhận được danh sách xe -> chuyển sang dùng trình duyệt")
        dung_trinh_duyet = True

    from playwright.sync_api import sync_playwright
    if "page" not in _pw:
        _pw["p"] = sync_playwright().start()
        _pw["page"] = _pw["p"].chromium.launch(headless=False).new_page()
    _pw["page"].goto(url, wait_until="domcontentloaded", timeout=60000)
    _pw["page"].wait_for_timeout(2500)
    return _pw["page"].content()

def doc_tin(url, text, title):
    # hãng, dòng xe, năm, mã tin lấy từ link: xe-vinfast-fadil-1.4-at-2021-7004915
    rest, nam, ma = url.rsplit("/", 1)[1][3:].rsplit("-", 2)
    hang, _, duoi = rest.partition("-")
    dong, _, phienban = duoi.partition("-")
    # giá và tỉnh lấy từ thuộc tính title của link: '... gia 445 Triệu - Hải Phòng'
    gia = tim(r"\bgi[áa]\s+(.+?)\s+-\s+", title) or tim(r"giá\s+(.+?)\s+-\s+", text)
    # đoạn thông số ngắn: '*Xe nhập khẩu, màu đỏ, máy xăng 1.5 L, số tự động, 5 chỗ, đã đi 33,000 km'
    m = re.search(r"\*?\s*Xe\s+(?:nhập khẩu|lắp ráp)", text)
    spec = re.split(r"\s\.\.\.|…|Liên hệ", text[m.start():])[0][:250] if m else ""
    km = tim(r"đã đi\s*([\d.,]+)\s*km", spec)
    nhienlieu = next((k for k in ["xăng", "dầu", "điện", "hybrid"] if k in spec.lower()), None)
    return {
        "id": ma,
        "condition": tim(r"^Xe\s+(cũ|mới)", text),
        "brand": hang.replace("_", " "),
        "model": dong.replace("_", " "),
        "variant": phienban.replace("_", " ").replace("-", " ") or None,
        "year": int(nam) if nam.isdigit() else None,
        "price_million": sang_trieu(gia),
        "province": tim(r"\s-\s+([^-]+?)\s*$", title),
        "origin": "nhập khẩu" if "nhập khẩu" in spec else ("trong nước" if "trong nước" in spec else None),
        "color": tim(r"màu\s+([^,]+)", spec),
        "fuel": nhienlieu,
        "engine_l": tim(r"(\d+(?:\.\d+)?)\s*L\b", spec),
        "gearbox": tim(r"số\s+(tự động|tay|sàn)", spec),
        "seats": tim(r"(\d+)\s*chỗ", spec),
        "km": int(re.sub(r"\D", "", km)) if km else None,
        "url": url,
    }

def doc_trang(html):
    soup = BeautifulSoup(html, "html.parser")
    tong = tim(r"Trang\s*\d+\s*/\s*(\d+)", soup.get_text(" ", strip=True))
    rows, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = urljoin(BASE, a["href"]).split("?")[0]
        m = ITEM_URL.match(href)
        if not m or m.group(1) in seen:
            continue
        li = a.find_parent("li") or a
        text = " ".join(li.get_text(" ", strip=True).split())
        try:
            row = doc_tin(href, text, a.get("title"))
        except Exception as e:
            print("  Không đọc được:", href, e)
            continue
        if row["price_million"] is not None: # tin không ghi giá thì bỏ
            seen.add(m.group(1))
            rows.append(row)
    return rows, int(tong) if tong else None

if __name__ == "__main__":
    tat_ca, da_co = [], set()
    for brand in BRANDS:
        print("==", brand)
        for trang in range(1, MAX_PAGES + 1):
            url = f"{BASE}/oto/{brand}" + (f"/page,{trang}" if trang > 1 else "")
            rows, tong = doc_trang(tai_trang(url))
            moi = [r for r in rows if r["id"] not in da_co]
            if not moi: # hết tin của hãng này
                break
            da_co.update(r["id"] for r in moi)
            tat_ca.extend(moi)
            print(f"  trang {trang}/{tong or '?'}: +{len(moi)} (tổng {len(tat_ca)})")
            if tong and trang >= tong:
                break
            time.sleep(DELAY + random.random() * 0.5)
        # lưu sau mỗi hãng để lỡ ngắt giữa chừng không mất dữ liệu
        pd.DataFrame(tat_ca).to_csv("cars_raw.csv", index=False, encoding="utf-8-sig")
    if "p" in _pw:
        _pw["p"].stop()
    print("Xong:", len(tat_ca), "tin -> cars_raw.csv")