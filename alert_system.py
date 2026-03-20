import time

ATTACK_LOG = "visits.txt"

def monitor():
    print("🛡️ 攻擊監控系統啟動...")
    last_size = 0

    while True:
        try:
            with open(ATTACK_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 有新訪問紀錄
            if len(lines) > last_size:
                new_lines = lines[last_size:]
                for line in new_lines:
                    ip = line.split("|")[0].strip()
                    print(f"📡 新訪客: {ip}")

                    # 模擬警報條件（大量請求）
                    if "127.0.0.1" in ip:
                        print("🚨 警告：偵測到高頻訪問 IP:", ip)

                last_size = len(lines)

        except FileNotFoundError:
            pass

        time.sleep(2)

if __name__ == "__main__":
    monitor()