import os
import sqlite3
import base64
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename
from fpdf import FPDF
from PyPDF2 import PdfReader, PdfWriter

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"

UPLOAD_FOLDER = '/tmp'
DB_PATH = '/tmp/database.db'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ANTI-CACHE SETTINGS
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

# --- PREMIUM CSS STYLES ---
PREMIUM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    body {
        margin: 0; padding: 20px; font-family: 'Inter', sans-serif;
        background: radial-gradient(circle at top left, #1e293b, #0f172a);
        color: white; min-height: 100vh;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
    }
    .glow {
        position: fixed; width: 300px; height: 300px;
        background: linear-gradient(to right, #38bdf8, #818cf8);
        border-radius: 50%; filter: blur(100px); opacity: 0.15; z-index: -1;
    }
    .card {
        background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        padding: 30px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1);
        width: 100%; max-width: 400px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); margin-bottom: 20px;
    }
    h2, h3 { text-align: center; background: linear-gradient(to right, #e2e8f0, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    input[type=text], input[type=number], input[type=password], input[type=file] {
        width: 100%; padding: 12px; margin: 8px 0 20px 0; background: rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; color: white;
        box-sizing: border-box; outline: none; transition: 0.3s;
    }
    input:focus { border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.1); }
    .btn {
        width: 100%; padding: 14px; background: linear-gradient(135deg, #38bdf8, #6366f1);
        border: none; border-radius: 10px; color: white; font-weight: 600; font-size: 16px;
        cursor: pointer; transition: 0.3s; margin-bottom: 10px;
    }
    .btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.4); }
    .btn:disabled { background: #475569; cursor: not-allowed; opacity: 0.7; }
    .btn-green { background: linear-gradient(135deg, #22c55e, #16a34a); }
    .btn-orange { background: linear-gradient(135deg, #f97316, #ea580c); }
    .btn-red { background: linear-gradient(135deg, #ef4444, #dc2626); }
    .btn-purple { background: linear-gradient(135deg, #a855f7, #7e22ce); }
    .btn-whatsapp { background: linear-gradient(135deg, #25D366, #128C7E); text-decoration: none; display: block; text-align: center; }
    .apps { display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; justify-content: space-between;}
    .apps a {
        flex: 1 1 45%; padding: 12px 0; text-align: center; background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; text-decoration: none; color: white; font-weight: 500;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { border: 1px solid rgba(255,255,255,0.1); padding: 12px; text-align: center; font-size: 14px;}
    img.qr { width: 220px; height: 220px; border-radius: 15px; margin: 10px auto; display: block; background: white; padding: 10px;}

    .status-box { padding: 25px; border-radius: 20px; text-align: center; margin-bottom: 20px; }
    .pending { background: rgba(234, 179, 8, 0.1); border: 1px solid #eab308; color: #fde047; }

    @keyframes popup {
        0% { transform: scale(0.5); opacity: 0; }
        100% { transform: scale(1); opacity: 1; }
    }
    .success-popup {
        background: rgba(34, 197, 94, 0.15); border: 2px solid #22c55e; color: #86efac;
        animation: popup 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        box-shadow: 0 0 30px rgba(34, 197, 94, 0.3);
    }
    .rejected { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #fca5a5; }

    .badge { padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    .b-pending { background: #eab308; color: black; }
    .b-approve { background: #22c55e; color: white; }
    .b-reject { background: #f97316; color: white; }
</style>
"""

def create_templates():
    index_html = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Premium Payment</title>""" + PREMIUM_CSS + """</head>
    <body>
        <div class="glow"></div>
        <div class="card" id="step1">
            <h2>Payment Gateway</h2>
            <label>Full Name</label>
            <input type="text" id="user_name" placeholder="Enter your name" required>
            <label>Amount (₹)</label>
            <input type="number" id="amount" placeholder="Enter Amount" required>
            <button class="btn" onclick="nextStep()">Proceed to Pay</button>
        </div>

        <div class="card" id="step2" style="display: none;">
            <h2>Scan & Pay</h2>
            <img id="qrcode" class="qr" src="" alt="QR Code">
            <button onclick="downloadQR()" class="btn btn-green">Download QR Code</button>

            <div class="apps">
                <a href="#" onclick="payVia('tez://upi/pay')">Google Pay</a>
                <a href="#" onclick="payVia('phonepe://pay')">PhonePe</a>
                <a href="#" onclick="payVia('paytmmp://pay')">Paytm</a>
                <a href="#" onclick="payVia('upi://pay')">More Apps</a>
            </div>

            <hr style="border-color: rgba(255,255,255,0.1); margin: 20px 0;">
            <h3>Upload Payment Proof</h3>
            <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data">
                <input type="hidden" name="name" id="hidden_name">
                <input type="hidden" name="amount" id="hidden_amount">
                <input type="file" name="screenshot" id="screenshot" accept="image/*" required>
                <button type="submit" id="submitBtn" class="btn">Submit Proof</button>
            </form>
        </div>

        <script>
            let upi_id = "{{ upi_id }}";
            function nextStep() {
                let name = document.getElementById('user_name').value;
                let amt = document.getElementById('amount').value;
                if(!name || !amt) { alert('Please enter name and amount'); return; }

                document.getElementById('hidden_name').value = name;
                document.getElementById('hidden_amount').value = amt;

                let upi_string = `upi://pay?pa=${upi_id}&pn=Admin&am=${amt}&tr=txn1234&cu=INR`;
                document.getElementById('qrcode').src = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(upi_string)}`;

                document.getElementById('step1').style.display = 'none';
                document.getElementById('step2').style.display = 'block';
            }

            async function downloadQR() {
                const imgSrc = document.getElementById('qrcode').src;
                const image = await fetch(imgSrc);
                const imageBlob = await image.blob();
                const imageURL = URL.createObjectURL(imageBlob);
                const link = document.createElement('a');
                link.href = imageURL;
                link.download = 'Payment_QR.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }

            function payVia(app_url) {
                let amt = document.getElementById('hidden_amount').value;
                window.location.href = `${app_url}?pa=${upi_id}&pn=Admin&am=${amt}&cu=INR`;
            }

            document.getElementById('uploadForm').onsubmit = function(e) {
                let btn = document.getElementById('submitBtn');
                if(btn.disabled) {
                    e.preventDefault();
                    return false;
                }
                btn.innerText = 'Uploading... Please wait';
                btn.disabled = true;
            };
        </script>
    </body></html>"""

    status_html = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="2">
    <title>Payment Status</title>""" + PREMIUM_CSS + """</head>
    <body>
        <div class="glow"></div>
        <div class="card" style="max-width: 450px;">
            <h2>Payment Status</h2>
            {% if status == 'Pending' %}
                <div class="status-box pending">
                    <h3 style="color:#fde047; margin:0">⏳ Pending Approval</h3>
                    <p style="font-size:14px;">Your payment of ₹{{ amount }} is being verified. (Auto Refreshing...)</p>
                </div>
                <a href="https://api.whatsapp.com/send?phone={{ whatsapp_number }}&text=Hello,%20please%20check%20my%20payment%20status.%20Name:%20{{ name }}%20Amount:%20{{ amount }}"
                   class="btn btn-whatsapp" target="_blank">Contact on WhatsApp</a>
            {% elif status == 'Approve' %}
                <div class="status-box success-popup">
                    <h1 style="margin:0; font-size:60px;">🎉</h1>
                    <h2 style="color:#86efac; margin:10px 0">Payment Successful!</h2>
                    <h3 style="margin:5px 0; color: white;">₹{{ amount }}</h3>
                    <p style="font-size:14px; opacity:0.8;">Thank you, {{ name }}. Your transaction has been approved.</p>
                </div>
            {% else %}
                <div class="status-box rejected">
                    <h3 style="color:#fca5a5; margin:0">❌ Payment Rejected</h3>
                    <p style="font-size:14px;">Your payment of ₹{{ amount }} was rejected. Contact admin for details.</p>
                </div>
            {% endif %}
        </div>
    </body></html>"""

    admin_html = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Admin Dashboard</title>""" + PREMIUM_CSS + """</head>
    <body>
        <div class="glow"></div>
        <div style="width: 100%; max-width: 900px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap:wrap; gap:10px;">
                <h2 style="margin:0;">Admin Panel</h2>
                <div style="display:flex; gap:10px;">
                    <button onclick="window.location.reload();" class="btn btn-blue" style="margin:0; padding:10px;">🔄 Refresh</button>
                    <a href="/logout" class="btn btn-red" style="margin:0; padding:10px; text-decoration:none;">Logout</a>
                </div>
            </div>

            <!-- ALL RECORDS SECTION -->
            <div class="card" style="max-width: 100%;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <h3 style="margin:0;">All Payment Records</h3>
                    <div style="display:flex; gap:10px;">
                        <button onclick="downloadPDF()" class="btn btn-purple" style="width:auto; padding:8px 15px; margin:0;">📥 Download Premium PDF</button>
                        <button onclick="resetRecords()" class="btn btn-red" style="width:auto; padding:8px 15px; margin:0;">⚠️ Reset All Records</button>
                    </div>
                </div>
                <div style="overflow-x: auto; margin-top: 15px;">
                    <table>
                        <tr><th>ID</th><th>Name</th><th>Amount</th><th>Status</th><th>Action</th></tr>
                        {% for row in all_records %}
                        <tr>
                            <td>#{{ row[0] }}</td>
                            <td>{{ row[1] }}</td>
                            <td>₹{{ row[2] }}</td>
                            <td>
                                {% if row[4] == 'Pending' %}<span class="badge b-pending">Pending</span>{% endif %}
                                {% if row[4] == 'Approve' %}<span class="badge b-approve">Approved</span>{% endif %}
                                {% if row[4] == 'Reject' %}<span class="badge b-reject">Rejected</span>{% endif %}
                            </td>
                            <td>
                                <form action="/action/{{ row[0] }}" method="post" style="margin:0;" onsubmit="return confirm('Are you sure you want to delete this record?');">
                                    <button name="action" value="Delete" class="btn btn-red" style="padding:6px 12px; font-size:12px; margin:0;">🗑 Delete</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>

            <!-- PENDING APPROVALS SECTION -->
            <div class="card" style="max-width: 100%;">
                <h3>Action Required (Pending)</h3>
                <div style="overflow-x: auto;">
                    <table>
                        <tr><th>Name</th><th>Amount</th><th>Screenshot</th><th>Action</th></tr>
                        {% for row in pending_proofs %}
                        <tr>
                            <td>{{ row[1] }}</td>
                            <td>₹{{ row[2] }}</td>
                            <td><a href="/{{ row[3] }}" target="_blank"><img src="/{{ row[3] }}" style="width:60px; border-radius:5px;"></a></td>
                            <td style="display:flex; gap:5px; justify-content:center;">
                                <form action="/action/{{ row[0] }}" method="post" style="margin:0;">
                                    <button name="action" value="Approve" class="btn btn-green" style="padding:8px; font-size:12px; margin:0;">✔ Approve</button>
                                </form>
                                <form action="/action/{{ row[0] }}" method="post" style="margin:0;">
                                    <button name="action" value="Reject" class="btn btn-orange" style="padding:8px; font-size:12px; margin:0;">✖ Reject</button>
                                </form>
                                <form action="/action/{{ row[0] }}" method="post" style="margin:0;" onsubmit="return confirm('Delete this pending payment forever?');">
                                    <button name="action" value="Delete" class="btn btn-red" style="padding:8px; font-size:12px; margin:0;">🗑 Delete</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>

            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                <div class="card" style="flex: 1; min-width: 300px;">
                    <h3>Change UPI ID</h3>
                    <form action="/update_upi" method="post">
                        <input type="text" name="new_upi" value="{{ current_upi }}" required>
                        <button type="submit" class="btn">Update UPI</button>
                    </form>
                </div>
                <div class="card" style="flex: 1; min-width: 300px;">
                    <h3>Change WhatsApp Number</h3>
                    <form action="/update_whatsapp" method="post">
                        <input type="text" name="new_whatsapp" value="{{ current_whatsapp }}" required>
                        <button type="submit" class="btn btn-whatsapp">Update WhatsApp</button>
                    </form>
                </div>
            </div>

            <div class="card" style="width: 100%; margin-top: 20px;">
                <h3>Change Admin Credentials</h3>
                <form action="/update_admin" method="post">
                    <input type="text" name="new_user" placeholder="New Username" required>
                    <input type="text" name="new_pass" placeholder="New Password" required>
                    <button type="submit" class="btn">Update & Logout</button>
                </form>
            </div>
        </div>

        <script>
            function downloadPDF() {
                let pwd = prompt("Create a password to lock this Premium PDF:");
                if(pwd) {
                    window.location.href = "/download_pdf?pwd=" + encodeURIComponent(pwd);
                }
            }

            function resetRecords() {
                let text = prompt("Warning: This will delete ALL payment records permanently.\\n\\nTo confirm, please type exactly:\\nCONFIRM RESET");
                if (text === 'CONFIRM RESET') {
                    window.location.href = "/reset_records";
                } else if (text !== null) {
                    alert("Text did not match! Data reset cancelled.");
                }
            }
        </script>
    </body></html>"""

    login_html = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Admin Login</title>""" + PREMIUM_CSS + """</head>
    <body>
        <div class="glow"></div>
        <div class="card">
            <h2>Admin Login</h2>
            <form method="post">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit" class="btn">Secure Login</button>
            </form>
            <p style="color:#ef4444; text-align:center;">{{ error }}</p>
        </div>
    </body></html>"""

    with open('templates/index.html', 'w') as f: f.write(index_html)
    with open('templates/status.html', 'w') as f: f.write(status_html)
    with open('templates/login.html', 'w') as f: f.write(login_html)
    with open('templates/admin.html', 'w') as f: f.write(admin_html)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY, username TEXT, password TEXT, upi_id TEXT, whatsapp_number TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, name TEXT, amount TEXT, image_path TEXT, status TEXT)')

    c.execute('SELECT * FROM admin')
    if not c.fetchone():
        c.execute("INSERT INTO admin (username, password, upi_id, whatsapp_number) VALUES (?, ?, ?, ?)",
                  ('7546982355', '7546982355', 'yourupi@ybl', '917546982355'))
    conn.commit()
    conn.close()

# --- ROUTES ---
@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT upi_id FROM admin WHERE id=1')
    res = c.fetchone()
    upi_id = res[0] if res else ""
    conn.close()
    return render_template('index.html', upi_id=upi_id)

@app.route('/upload', methods=['POST'])
def upload():
    name = request.form.get('name', 'Unknown')
    amount = request.form.get('amount', '0')
    file = request.files.get('screenshot')
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO payments (name, amount, image_path, status) "
            "VALUES (?, ?, ?, 'Pending')",
            (name, amount, filepath)
        )
        payment_id = c.lastrowid
        conn.commit()
        conn.close()

        token = base64.urlsafe_b64encode(f"dolat_{payment_id}_secure".encode()).decode()
        return redirect(url_for('status', pid=token))
    return "Error: No file uploaded"

@app.route('/status/<pid>')
def status(pid):
    try:
        decoded = base64.urlsafe_b64decode(pid.encode()).decode()
        real_id = int(decoded.split('_')[1])
    except:
        return "Invalid Payment Link"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, amount, status FROM payments WHERE id=?", (real_id,))
    data = c.fetchone()
    
    c.execute("SELECT whatsapp_number FROM admin WHERE id=1")
    wa_res = c.fetchone()
    whatsapp_number = wa_res[0] if wa_res else "917546982355"
    conn.close()

    if data:
        return render_template('status.html', name=data[0], amount=data[1], status=data[2], whatsapp_number=whatsapp_number)
    return "Not Found"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM admin WHERE username=? AND password=?', (user, pw))
        admin = c.fetchone()
        conn.close()

        if admin:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html', error="")

@app.route('/admin')
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, name, amount, image_path, status FROM payments WHERE status='Pending'")
    pending_proofs = c.fetchall()

    c.execute("SELECT id, name, amount, image_path, status FROM payments ORDER BY id DESC")
    all_records = c.fetchall()

    c.execute('SELECT upi_id, whatsapp_number FROM admin WHERE id=1')
    res = c.fetchone()
    current_upi = res[0] if res else ""
    current_whatsapp = res[1] if res else "917546982355"
    conn.close()
    return render_template('admin.html', pending_proofs=pending_proofs, all_records=all_records, current_upi=current_upi, current_whatsapp=current_whatsapp)

@app.route('/update_whatsapp', methods=['POST'])
def update_whatsapp():
    if not session.get('logged_in'): return redirect(url_for('login'))
    new_whatsapp = request.form['new_whatsapp']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE admin SET whatsapp_number=? WHERE id=1", (new_whatsapp,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/reset_records')
def reset_records():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM payments")
    conn.commit()
    conn.close()

    folder = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

    return redirect(url_for('admin'))

@app.route('/download_pdf')
def download_pdf():
    if not session.get('logged_in'): return redirect(url_for('login'))
    pwd = request.args.get('pwd')
    if not pwd:
        return "Password missing!", 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, amount, status FROM payments ORDER BY id DESC")
    records = c.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(56, 189, 248)
    pdf.cell(0, 15, txt="PREMIUM PAYMENT RECORDS", ln=True, align='C')
    pdf.ln(5)

    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 12)

    pdf.cell(20, 10, "ID", border=1, fill=True, align='C')
    pdf.cell(70, 10, "Customer Name", border=1, fill=True, align='C')
    pdf.cell(40, 10, "Amount (Rs)", border=1, fill=True, align='C')
    pdf.cell(60, 10, "Status", border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(0, 0, 0)

    for i, row in enumerate(records):
        if i % 2 == 0:
            pdf.set_fill_color(241, 245, 249)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.cell(20, 10, str(row[0]), border=1, fill=True, align='C')
        pdf.cell(70, 10, str(row[1]), border=1, fill=True, align='C')
        pdf.cell(40, 10, str(row[2]), border=1, fill=True, align='C')
        pdf.cell(60, 10, str(row[3]), border=1, fill=True, align='C')
        pdf.ln()

    temp_pdf = "temp_records.pdf"
    pdf.output(temp_pdf)

    reader = PdfReader(temp_pdf)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(pwd)
    secure_pdf = "Payment_History_Secure.pdf"
    with open(secure_pdf, "wb") as f:
        writer.write(f)

    os.remove(temp_pdf)
    return send_file(secure_pdf, as_attachment=True)

@app.route('/update_upi', methods=['POST'])
def update_upi():
    if not session.get('logged_in'): return redirect(url_for('login'))
    new_upi = request.form['new_upi']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE admin SET upi_id=? WHERE id=1", (new_upi,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/action/<int:pid>', methods=['POST'])
def action(pid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    act = request.form['action']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if act == 'Delete':
        c.execute("DELETE FROM payments WHERE id=?", (pid,))
    else:
        c.execute("UPDATE payments SET status=? WHERE id=?", (act, pid))

    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/update_admin', methods=['POST'])
def update_admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    new_user = request.form['new_user']
    new_pass = request.form['new_pass']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE admin SET username=?, password=? WHERE id=1", (new_user, new_pass))
    conn.commit()
    conn.close()
    session.clear()
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    create_templates()
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
