from flask import Flask, request, jsonify, render_template_string
import sqlite3
import secrets
import string
import hashlib
from datetime import datetime, timedelta

app = Flask(__name__)
DB_PATH = "licenses.db"
ADMIN_TOKEN = "myapp-admin-2024"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT NULL,
            hwid TEXT DEFAULT NULL,
            expires_at TEXT DEFAULT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# ---------- WEB SAYFALARI ----------

REGISTER_PAGE = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>XEAN — Kayıt Ol</title>
<style>
body { background:#0d0d0d; color:#fff; font-family: 'Segoe UI', sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
.card { background:#141414; padding:40px; border-radius:12px; border:1px solid #2a0000; width:340px; text-align:center; }
h1 { color:#ff4d5a; letter-spacing:4px; margin-bottom:5px; }
p.sub { color:#666; font-size:12px; margin-bottom:25px; }
input { width:100%; padding:12px; margin:8px 0; background:#0d0d0d; border:1px solid #e63946; border-radius:6px; color:#fff; box-sizing:border-box; font-size:14px; }
button { width:100%; padding:12px; margin-top:15px; background:#e63946; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:14px; }
button:hover { background:#c1121f; }
.msg { margin-top:15px; font-size:13px; }
.error { color:#ff4d5a; }
.success { color:#4caf50; }
a { color:#ff4d5a; text-decoration:none; font-size:12px; }
</style>
</head>
<body>
<div class="card">
  <h1>XEAN</h1>
  <p class="sub">HESAP OLUŞTUR</p>
  <form id="regForm">
    <input type="email" id="email" placeholder="Email adresiniz" required>
    <input type="password" id="password" placeholder="Şifre" required>
    <button type="submit">KAYIT OL</button>
  </form>
  <div class="msg" id="msg"></div>
  <br>
  <a href="/login">Zaten hesabın var mı? Giriş yap</a>
</div>
<script>
document.getElementById('regForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const msg = document.getElementById('msg');
  msg.textContent = 'İşleniyor...';
  msg.className = 'msg';
  const res = await fetch('/api/register', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email, password})
  });
  const data = await res.json();
  if (data.success) {
    msg.textContent = 'Kayıt başarılı! Girişe yönlendiriliyorsunuz...';
    msg.className = 'msg success';
    setTimeout(() => window.location.href = '/login', 1500);
  } else {
    msg.textContent = data.reason || 'Bir hata oluştu';
    msg.className = 'msg error';
  }
});
</script>
</body>
</html>
"""

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>XEAN — Giriş Yap</title>
<style>
body { background:#0d0d0d; color:#fff; font-family: 'Segoe UI', sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
.card { background:#141414; padding:40px; border-radius:12px; border:1px solid #2a0000; width:340px; text-align:center; }
h1 { color:#ff4d5a; letter-spacing:4px; margin-bottom:5px; }
p.sub { color:#666; font-size:12px; margin-bottom:25px; }
input { width:100%; padding:12px; margin:8px 0; background:#0d0d0d; border:1px solid #e63946; border-radius:6px; color:#fff; box-sizing:border-box; font-size:14px; }
button { width:100%; padding:12px; margin-top:15px; background:#e63946; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:14px; }
button:hover { background:#c1121f; }
.msg { margin-top:15px; font-size:13px; }
.error { color:#ff4d5a; }
.success { color:#4caf50; }
.info-box { background:#0d0d0d; border:1px solid #2a0000; border-radius:8px; padding:15px; margin-top:20px; text-align:left; font-size:13px; }
.info-box p { margin:5px 0; }
a { color:#ff4d5a; text-decoration:none; font-size:12px; }
</style>
</head>
<body>
<div class="card">
  <h1>XEAN</h1>
  <p class="sub">HESABINA GİRİŞ YAP</p>
  <form id="loginForm">
    <input type="email" id="email" placeholder="Email adresiniz" required>
    <input type="password" id="password" placeholder="Şifre" required>
    <button type="submit">GİRİŞ YAP</button>
  </form>
  <div class="msg" id="msg"></div>
  <div id="accountInfo"></div>
  <br>
  <a href="/register">Hesabın yok mu? Kayıt ol</a>
</div>
<script>
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const msg = document.getElementById('msg');
  const infoBox = document.getElementById('accountInfo');
  msg.textContent = 'Kontrol ediliyor...';
  msg.className = 'msg';
  infoBox.innerHTML = '';
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email, password})
  });
  const data = await res.json();
  if (data.success) {
    msg.textContent = 'Giriş başarılı!';
    msg.className = 'msg success';
    let planText = data.plan ? data.plan : 'Henüz plan atanmadı';
    infoBox.innerHTML = `<div class="info-box"><p><b>Plan:</b> ${planText}</p><p><b>Kalan Süre:</b> ${data.remaining || '-'}</p></div>`;
  } else {
    msg.textContent = data.reason || 'Giriş başarısız';
    msg.className = 'msg error';
  }
});
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return LOGIN_PAGE

@app.route("/register")
def register_page():
    return REGISTER_PAGE

@app.route("/login")
def login_page():
    return LOGIN_PAGE

# ---------- API ----------

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    if not email or not password:
        return jsonify({"success": False, "reason": "Email ve şifre gerekli"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "reason": "Şifre en az 6 karakter olmalı"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, hash_password(password), datetime.utcnow().isoformat())
        )
        conn.commit()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "reason": "Bu email zaten kayıtlı"}), 400
    finally:
        conn.close()

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    hwid = data.get("hwid", "").strip()  # opsiyonel, program içi girişten gelir

    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not row or row["password_hash"] != hash_password(password):
        conn.close()
        return jsonify({"success": False, "reason": "Email veya şifre hatalı"})

    if not row["is_active"]:
        conn.close()
        return jsonify({"success": False, "reason": "Hesabınız devre dışı"})

    if not row["plan"]:
        conn.close()
        return jsonify({"success": True, "plan": None, "remaining": "Plan atanmadı"})

    # HWID kontrolü (program içi girişte)
    if hwid:
        if row["hwid"] is not None and row["hwid"] != hwid:
            conn.close()
            return jsonify({"success": False, "reason": "Hesabınız başka bir cihazda kullanılıyor"})
        if row["hwid"] is None:
            conn.execute("UPDATE users SET hwid = ? WHERE email = ?", (hwid, email))
            conn.commit()

    remaining_str = "Sınırsız"
    if row["expires_at"]:
        expires = datetime.fromisoformat(row["expires_at"])
        if datetime.utcnow() > expires:
            conn.close()
            return jsonify({"success": False, "reason": "Aboneliğinizin süresi dolmuş"})
        diff = expires - datetime.utcnow()
        remaining_str = f"{diff.days} gün {diff.seconds // 3600} saat"

    conn.close()
    return jsonify({"success": True, "plan": row["plan"], "remaining": remaining_str})

# ---------- ADMIN: KULLANICIYA PLAN ATA ----------

@app.route("/api/admin/assign_plan", methods=["POST"])
def assign_plan():
    auth = request.headers.get("X-Admin-Token")
    if auth != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    email = data.get("email", "").strip().lower()
    plan = data.get("plan", "lifetime")

    if plan not in ["weekly", "monthly", "lifetime"]:
        return jsonify({"error": "Invalid plan"}), 400

    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    now = datetime.utcnow()
    if plan == "weekly":
        expires_at = (now + timedelta(days=7)).isoformat()
    elif plan == "monthly":
        expires_at = (now + timedelta(days=30)).isoformat()
    else:
        expires_at = None

    conn.execute("UPDATE users SET plan = ?, expires_at = ? WHERE email = ?", (plan, expires_at, email))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "email": email, "plan": plan, "expires_at": expires_at})

@app.route("/api/admin/list_users", methods=["GET"])
def list_users():
    auth = request.headers.get("X-Admin-Token")
    if auth != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT id, email, plan, expires_at, is_active, created_at FROM users").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
ADMIN_PAGE = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>XEAN — Admin Panel</title>
<style>
body { background:#0d0d0d; color:#fff; font-family: 'Segoe UI', sans-serif; margin:0; padding:30px; }
h1 { color:#ff4d5a; letter-spacing:3px; }
.login-box { max-width:340px; margin:100px auto; background:#141414; padding:30px; border-radius:12px; border:1px solid #2a0000; text-align:center; }
input { width:100%; padding:10px; margin:8px 0; background:#0d0d0d; border:1px solid #e63946; border-radius:6px; color:#fff; box-sizing:border-box; }
button { padding:10px 20px; background:#e63946; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer; }
button:hover { background:#c1121f; }
table { width:100%; border-collapse:collapse; margin-top:20px; }
th, td { padding:10px; border-bottom:1px solid #2a0000; text-align:left; font-size:13px; }
th { color:#ff4d5a; }
select { padding:6px; background:#0d0d0d; color:#fff; border:1px solid #e63946; border-radius:4px; }
.badge { padding:3px 8px; border-radius:4px; font-size:11px; font-weight:bold; }
.badge-active { background:#1a4d2e; color:#4caf50; }
.badge-none { background:#2a2a2a; color:#888; }
.stats { display:flex; gap:15px; margin-bottom:20px; }
.stat-box { background:#141414; padding:15px 25px; border-radius:8px; border:1px solid #2a0000; }
.stat-box .num { font-size:24px; font-weight:bold; color:#ff4d5a; }
.stat-box .label { font-size:11px; color:#666; }
#msg { margin-top:10px; font-size:13px; }
</style>
</head>
<body>
<div id="loginArea">
  <div class="login-box">
    <h1>XEAN ADMIN</h1>
    <input type="password" id="adminToken" placeholder="Admin Token">
    <button onclick="doLogin()">GİRİŞ</button>
    <div id="loginMsg" style="color:#ff4d5a; margin-top:10px; font-size:13px;"></div>
  </div>
</div>

<div id="panelArea" style="display:none;">
  <h1>XEAN — YÖNETİM PANELİ</h1>
  <div class="stats" id="stats"></div>
  <table>
    <thead>
      <tr><th>Email</th><th>Plan</th><th>Bitiş</th><th>Durum</th><th>Kayıt</th><th>Aksiyon</th></tr>
    </thead>
    <tbody id="userTable"></tbody>
  </table>
</div>

<script>
let token = '';

function doLogin() {
  token = document.getElementById('adminToken').value;
  fetch('/api/admin/list_users', { headers: { 'X-Admin-Token': token } })
    .then(res => {
      if (!res.ok) throw new Error('unauthorized');
      return res.json();
    })
    .then(data => {
      document.getElementById('loginArea').style.display = 'none';
      document.getElementById('panelArea').style.display = 'block';
      renderUsers(data);
    })
    .catch(() => {
      document.getElementById('loginMsg').textContent = 'Hatalı token';
    });
}

function renderUsers(users) {
  const total = users.length;
  const active = users.filter(u => u.plan).length;
  document.getElementById('stats').innerHTML = `
    <div class="stat-box"><div class="num">${total}</div><div class="label">TOPLAM KAYIT</div></div>
    <div class="stat-box"><div class="num">${active}</div><div class="label">AKTİF ÜYELİK</div></div>
  `;

  const tbody = document.getElementById('userTable');
  tbody.innerHTML = '';
  users.forEach(u => {
    const tr = document.createElement('tr');
    const badge = u.plan ? `<span class="badge badge-active">${u.plan}</span>` : `<span class="badge badge-none">Yok</span>`;
    const expires = u.expires_at ? new Date(u.expires_at).toLocaleDateString('tr-TR') : (u.plan ? 'Sınırsız' : '-');
    tr.innerHTML = `
      <td>${u.email}</td>
      <td>${badge}</td>
      <td>${expires}</td>
      <td>${u.is_active ? 'Aktif' : 'Pasif'}</td>
      <td>${new Date(u.created_at).toLocaleDateString('tr-TR')}</td>
      <td>
        <select id="plan-${u.id}">
          <option value="weekly">Haftalık</option>
          <option value="monthly">Aylık</option>
          <option value="lifetime">Lifetime</option>
        </select>
        <button onclick="assignPlan('${u.email}', ${u.id})">Ata</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function assignPlan(email, id) {
  const plan = document.getElementById('plan-' + id).value;
  fetch('/api/admin/assign_plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
    body: JSON.stringify({ email, plan })
  })
  .then(res => res.json())
  .then(() => doLogin());
}
</script>
</body>
</html>
"""

@app.route("/admin")
def admin_page():
    return ADMIN_PAGE
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)