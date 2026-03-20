from flask import Flask, request, render_template, render_template_string, redirect, url_for, abort
from datetime import datetime
import os, base64
from ctf_lab import ctf
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

SECRET = base64.b64decode("MTIzNDU2Nzg5MA==").decode()

app = Flask(__name__)
visitors = []
VISIT_FILE = "visits.txt"
failed_attempts = {}  # 記錄每個IP錯誤次數
blocked_ips = set()   # 被封鎖IP
BLOCK_FILE = "blocked_ips.txt"
BLOCK_TIME_FILE = "blocked_time.txt"
app.register_blueprint(ctf)
# ⭐ 資料庫設定（SQLite）
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///security_lab.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
# =====================
# 資料庫模型（Database Models）
# =====================

# ⭐ 釣魚帳密紀錄（Phishing Log）
class PhishingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))
    ip = db.Column(db.String(50))
    time = db.Column(db.String(50))

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    time = db.Column(db.String(50))


class BlockedIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True)
    block_time = db.Column(db.Integer)


class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50))
    attempts = db.Column(db.Integer, default=0)

# ⭐ 使用者帳號資料庫（登入用）
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))  # CTF故意明文（方便滲透練習）

def reset_failed_attempt(ip):
    if ip in failed_attempts:
        failed_attempts.pop(ip)


def save_blocked_ips():
    with open(BLOCK_FILE, "w") as f:
        for ip in blocked_ips:
            f.write(ip + "\n")


def save_block_time(ip):
    import time
    with open(BLOCK_TIME_FILE, "a") as f:
        f.write(f"{ip}|{int(time.time())}\n")


def load_blocked_ips():
    blocked_ips.clear()  # ⭐ 關鍵修正：先清空再重新讀取
    if os.path.exists(BLOCK_FILE):
        with open(BLOCK_FILE, "r") as f:
            for line in f:
                ip = line.strip()
                if ip:
                    blocked_ips.add(ip)


# 啟動時讀取
load_blocked_ips()

# =====================
# 全站訪客紀錄（只保留一個）
# =====================
@app.before_request
def log_visit():
    data = {
        "ip": request.remote_addr,
        "ua": request.headers.get("User-Agent"),
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 存入資料庫（取代 visits.txt）
    visitor = Visitor(
        ip=data["ip"],
        user_agent=data["ua"],
        time=data["time"]
    )
    db.session.add(visitor)
    db.session.commit()


# =====================
# 首頁
# =====================
@app.route("/")
@app.route("/home")
def index():
    return render_template("index.html")


# =====================
# 🔐 Header 隱藏頁（方法三）
# =====================
@app.route("/visit")
def visit():
    if request.headers.get("X-Admin") == "true":
        ip = request.remote_addr
        print(f"[+] Header bypass by {ip}")
        return redirect(url_for("users"))
    else:
        abort(404)


# ⚠️ 管理頁（CTF 洩漏點）
@app.route("/users")
def users():
    # ⭐ 先檢查權限（CTF Header Bypass）
    if request.headers.get("X-Admin") != "true":
        abort(404)

    ip = request.remote_addr
    print(f"[+] Header bypass by {ip}")

    # ⭐ 從資料庫讀取訪客
    db_visitors = Visitor.query.order_by(Visitor.id.desc()).all()

    # ⭐ 從資料庫讀取被封鎖IP
    db_blocked_ips = BlockedIP.query.all()

    # ⭐ CTF 洩漏點：文字檔封鎖IP
    file_blocked_ips = []
    if os.path.exists(BLOCK_FILE):
        with open(BLOCK_FILE, "r") as f:
            file_blocked_ips = [line.strip() for line in f if line.strip()]

    # ⭐ CTF 洩漏點：封鎖時間
    block_times = []
    if os.path.exists(BLOCK_TIME_FILE):
        with open(BLOCK_TIME_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    ip, t = line.split("|")
                    block_times.append({
                        "ip": ip,
                        "time": t
                    })

    return render_template(
        "users.html",
        visitors=db_visitors,
        blocked_db=db_blocked_ips,
        blocked_file=file_blocked_ips,
        block_times=block_times
    )
# ✅ 弱登入（CTF 用）
@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""

    def get_real_ip():
        if request.headers.get("X-Forwarded-For"):
            return request.headers.get("X-Forwarded-For")
        return request.remote_addr

    ip = get_real_ip()

    # ⭐ 檢查資料庫是否封鎖
    blocked = BlockedIP.query.filter_by(ip=ip).first()

    if blocked:
        return f"""
        <h1 style='color:red;'>🚨 SECURITY ALERT</h1>
        <p>偵測到暴力破解行為</p>
        <p>你的IP: {ip}</p>
        <p>此IP已被系統封鎖</p>
        """

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # ⭐ 初始化錯誤次數
        if ip not in failed_attempts:
            failed_attempts[ip] = 0

        # ⭐ 資料庫驗證帳密
        user = User.query.filter_by(username=username, password=password).first()

        # ===== 登入成功 =====
        if user:

            failed_attempts[ip] = 0

            print(f"[+] 使用者登入成功: {username} 來自 {ip}")

            return redirect(url_for("xss_lab"))

        # ===== 登入失敗 =====
        else:

            failed_attempts[ip] += 1
            attempts = failed_attempts[ip]

            print(f"[!] IP {ip} 錯誤登入次數: {attempts}")

            # ⭐ 超過 100 次封鎖
            if attempts >= 100:

                import time

                new_block = BlockedIP(
                    ip=ip,
                    block_time=int(time.time())
                )

                db.session.add(new_block)
                db.session.commit()

                print(f"🚨 已封鎖攻擊IP: {ip}")

                failed_attempts.pop(ip, None)

                return f"""
                <h1 style='color:red;'>🚨 已封鎖</h1>
                <p>偵測到暴力破解攻擊</p>
                <p>IP: {ip}</p>
                <p>此行為已被記錄</p>
                """

            message = f"帳號或密碼錯誤（{attempts}/100）"

    return render_template("login.html", message=message)

# 🎣 釣魚登入頁（CTF用）
@app.route("/phish", methods=["GET", "POST"])
def phishing_login():
    message = ""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        ip = request.remote_addr
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ⭐ 偷偷存入資料庫（重點）
        log = PhishingLog(
            username=username,
            password=password,
            ip=ip,
            time=now
        )
        db.session.add(log)
        db.session.commit()

        print(f"🎣 捕獲帳密: {username} / {password} 來自IP: {ip}")

        # 假裝登入失敗（更真實）
        message = "帳號或密碼錯誤"

    return render_template("phish.html", message=message)


# =====================
# XSS LAB
# =====================
@app.route("/xss", methods=["GET", "POST"])
def xss_lab():
    content = ""
    if request.method == "POST":
        content = request.form.get("content", "")
    return render_template("XSS.html", content=content)

# 🧠 查看釣魚結果（管理員用）
@app.route("/phish_logs")
def phish_logs():

    # ⭐ 只有帶 X-Admin:true 才能進入
    if request.headers.get("X-Admin") == "true":
        ip = request.remote_addr
        print(f"[+] Header bypass by {ip}")

        logs = PhishingLog.query.all()
        return render_template("phish_logs.html", logs=logs)

    else:
        abort(404)


@app.route("/unblock")
def unblock_ip():
    ip = request.args.get("ip")

    if not ip:
        return "請提供 IP"

    if ip in blocked_ips:
        blocked_ips.discard(ip)
        reset_failed_attempt(ip)  # ⭐ 同步清除錯誤次數
        save_blocked_ips()
        return f"✅ 已解除封鎖 IP: {ip}"
    else:
        return f"⚠ IP {ip} 不在封鎖名單"


# 🛡️ 安全監控儀表板
@app.route("/security")
def security_dashboard():
    return render_template(
        "security.html",
        blocked=blocked_ips,
        attempts=failed_attempts
    )

# 💣 SQL Injection 測試頁（給 sqlmap 用）
@app.route("/sqli")
def sqli():
    user_id = request.args.get("id")

    try:
        query = text(f"SELECT * FROM user WHERE id = {user_id}")  # 💣 故意漏洞
        result = db.session.execute(query)

        rows = result.fetchall()

        return str(rows)

    except Exception as e:
        return f"SQL Error: {e}"

# ⭐ 啟動時建立資料庫
with app.app_context():
    db.create_all()

    # ⭐ 建立預設帳號（只會建立一次）
    if not User.query.filter_by(username="vincent").first():
        default_user = User(
            username="vincent",
            password="1234"  # CTF弱密碼
        )
        db.session.add(default_user)
        db.session.commit()
        print("✅ 已建立預設帳號: vincent / 1234")
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)