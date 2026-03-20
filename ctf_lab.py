from flask import Blueprint, request, render_template_string

ctf = Blueprint("ctf", __name__)

# =====================
# 1️⃣ XSS 關卡
# =====================
@ctf.route("/lab/xss", methods=["GET", "POST"])
def xss_lab():
    content = ""
    if request.method == "POST":
        content = request.form.get("content", "")

    html = f"""
    <h1>🧪 XSS Challenge</h1>
    <form method="POST">
        <input name="content" placeholder="輸入內容">
        <button type="submit">送出</button>
    </form>
    <div>
        {content}
    </div>
    <p>FLAG: FLAG{{xss_master}}</p>
    """
    return render_template_string(html)


# =====================
# 2️⃣ SQL Injection 關卡（模擬）
# =====================
@ctf.route("/lab/sqli", methods=["GET", "POST"])
def sqli_lab():
    message = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # 故意做成漏洞
        if "' OR '1'='1" in username:
            message = "🎉 SQL Injection 成功! FLAG{SQLI_WIN}"
        else:
            message = "登入失敗"

    html = f"""
    <h1>💉 SQL Injection Lab</h1>
    <form method="POST">
        <input name="username" placeholder="username">
        <input name="password" placeholder="password">
        <button type="submit">Login</button>
    </form>
    <p>{message}</p>
    """
    return render_template_string(html)


# =====================
# 3️⃣ 暴力破解關卡
# =====================
@ctf.route("/lab/bruteforce")
def brute_lab():
    return """
    <h1>🔓 Brute Force Challenge</h1>
    <p>提示：密碼是4位數字</p>
    <p>FLAG: FLAG{bruteforce_ready}</p>
    """