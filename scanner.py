import requests
from concurrent.futures import ThreadPoolExecutor

TARGET = "http://127.0.0.1:8080"

# 常見駭客掃描路徑字典
paths = [
    "/admin",
    "/login",
    "/users",
    "/security",
    "/backup",
    "/.env",
    "/config",
    "/visit",
    "/hidden",
    "/debug"
]

def scan(path):
    url = TARGET + path
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            print(f"[+] 發現頁面: {url}")
        elif r.status_code == 403:
            print(f"[!] 受保護頁面: {url}")
        else:
            print(f"[-] 不存在: {url}")
    except:
        print(f"[X] 無法連線: {url}")

print("🔍 開始漏洞掃描...")

with ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(scan, paths)

print("✅ 掃描完成")