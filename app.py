import streamlit as st
import sqlite3, os, threading, time, requests, pandas as pd
import plotly.express as px, plotly.graph_objects as go
import smtplib, random, string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, date
from io import BytesIO
from math import sqrt
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch

st.set_page_config(page_title="MedPanel Pro", layout="wide",
                   page_icon="🏥", initial_sidebar_state="collapsed")

# ─── KEEP-ALIVE ──────────────────────────────────────────────────────────────
@st.cache_resource
def _keep_alive():
    def _ping():
        while True:
            time.sleep(290)
            try:
                requests.get("https://consultorio-bot.streamlit.app/_stcore/health", timeout=10)
            except Exception:
                pass
    threading.Thread(target=_ping, daemon=True).start()
    return True
_keep_alive()

# ─── CONFIG ──────────────────────────────────────────────────────────────────
ADMIN_USER      = "admin"
ADMIN_PASS      = "admindasoto88"

def _s(key, default=""):
    try: return st.secrets.get(key, default)
    except: return default

CLINIC_NAME     = _s("CLINIC_NAME",      "Consultorio Médico")
DOCTOR_NAME     = _s("DOCTOR_NAME",      "Dr. Médico")
SPECIALTY       = _s("DOCTOR_SPECIALTY", "Medicina General")
PHONE           = _s("PHONE_NUMBER",     "")
MP_TOKEN        = _s("MP_ACCESS_TOKEN",  "")
CONSULTA_PRECIO = float(_s("CONSULTA_PRECIO", "500"))
ADMIN_EMAIL     = _s("ADMIN_EMAIL",      "")
SMTP_SERVER     = _s("SMTP_SERVER",      "smtp.gmail.com")
SMTP_PORT       = int(_s("SMTP_PORT",    "587"))
SMTP_USER       = _s("SMTP_USER",        "")
SMTP_PASS       = _s("SMTP_PASS",        "")

# ─── CSS GLOBAL ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* { font-family:'Inter',sans-serif !important; }
#MainMenu,footer,header,[data-testid="stToolbar"] { display:none !important; }
[data-testid="stAppViewContainer"] { padding:0 !important; }
[data-testid="block-container"] { padding-top:1rem !important; }

/* ── LANDING CSS ── */
.hero-wrap {
    background: linear-gradient(135deg,#061a2e 0%,#0d3d5e 30%,#0a6b5e 60%,#064e3b 100%);
    background-size:300% 300%;
    animation: heroShift 12s ease infinite;
    border-radius:0 0 40px 40px;
    padding:3rem 2rem 2.5rem;
    margin:-1rem -1rem 2rem -1rem;
    position:relative; overflow:hidden;
}
.hero-wrap::before {
    content:'';
    position:absolute; top:-50%; left:-50%; width:200%; height:200%;
    background: radial-gradient(ellipse at center, rgba(14,212,172,.08) 0%, transparent 70%);
    animation: rotateGlow 20s linear infinite;
}
.hero-wrap::after {
    content:'';
    position:absolute; bottom:0; left:0; right:0; height:80px;
    background:linear-gradient(to bottom, transparent, rgba(6,26,46,.4));
}
@keyframes heroShift {
    0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%}
}
@keyframes rotateGlow {
    0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)}
}
@keyframes fadeUp {
    from{opacity:0;transform:translateY(30px)} to{opacity:1;transform:translateY(0)}
}
@keyframes pulse {
    0%,100%{transform:scale(1)} 50%{transform:scale(1.05)}
}
@keyframes float {
    0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)}
}
.hero-title {
    font-size:3.2rem;font-weight:800;color:white;text-align:center;
    margin:0;line-height:1.15;animation:fadeUp .8s ease;
    text-shadow:0 4px 30px rgba(0,0,0,.4);
    position:relative;z-index:1;
}
.hero-subtitle {
    font-size:1.15rem;color:rgba(255,255,255,.82);text-align:center;
    margin:.8rem 0 0;animation:fadeUp 1s ease .2s both;
    position:relative;z-index:1;
}
.hero-badge {
    display:inline-block;background:rgba(255,255,255,.15);
    backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.25);
    border-radius:30px;padding:6px 18px;font-size:.82rem;color:white;
    margin:4px 6px;animation:fadeUp 1s ease .4s both;
}
.feature-card {
    background:rgba(255,255,255,.08);backdrop-filter:blur(20px);
    border:1px solid rgba(255,255,255,.15);border-radius:16px;
    padding:1.4rem;text-align:center;color:white;
    transition:transform .3s,box-shadow .3s;animation:fadeUp 1s ease .6s both;
    position:relative;z-index:1;
}
.feature-card:hover{transform:translateY(-6px);box-shadow:0 20px 40px rgba(0,0,0,.3)}
.feature-icon{font-size:2.4rem;margin-bottom:.6rem;animation:float 3s ease infinite}
.feature-title{font-size:1rem;font-weight:700;margin-bottom:.3rem}
.feature-desc{font-size:.82rem;opacity:.8}

/* ── GLASS LOGIN ── */
.glass-login {
    background:rgba(255,255,255,.12);backdrop-filter:blur(30px);
    -webkit-backdrop-filter:blur(30px);
    border:1px solid rgba(255,255,255,.25);
    border-radius:24px;padding:2.4rem;
    box-shadow:0 30px 60px rgba(0,0,0,.35);
    animation:fadeUp .8s ease;
}
.login-logo{font-size:3.5rem;text-align:center;animation:pulse 2s ease infinite;margin-bottom:.5rem}
.login-title{font-size:1.6rem;font-weight:700;color:white;text-align:center;margin:0 0 .3rem}
.login-sub{font-size:.88rem;color:rgba(255,255,255,.7);text-align:center;margin-bottom:1.5rem}

/* ── INFO CARDS ── */
.info-feature {
    background:linear-gradient(135deg,rgba(14,116,144,.2),rgba(6,78,59,.2));
    border:1px solid rgba(14,116,144,.4);border-radius:16px;padding:1.5rem;
    color:white;margin-bottom:1rem;
}
.price-card {
    background:linear-gradient(135deg,#0d4f6c,#064e3b);border-radius:20px;
    padding:2rem;color:white;text-align:center;
    border:2px solid transparent;transition:border .3s,transform .3s;
}
.price-card:hover{border-color:rgba(255,255,255,.4);transform:scale(1.02)}
.price-card.featured{border-color:rgba(250,204,21,.6);background:linear-gradient(135deg,#0e7490,#065f46)}
.price-badge{background:rgba(250,204,21,.25);color:#fde047;border-radius:20px;
             padding:3px 12px;font-size:.75rem;font-weight:700;display:inline-block;margin-bottom:.5rem}
.price-amount{font-size:2.6rem;font-weight:800;margin:.5rem 0}
.price-period{font-size:.85rem;opacity:.7}
.price-feature{font-size:.85rem;padding:.25rem 0;border-bottom:1px solid rgba(255,255,255,.1)}

/* ── DASHBOARD CSS ── */
.dash-banner {
    background:linear-gradient(135deg,#0d4f6c,#0e7490,#0891b2);
    border-radius:16px;padding:1.4rem 2rem;margin-bottom:1.2rem;
    color:white;display:flex;align-items:center;justify-content:space-between;
    box-shadow:0 8px 32px rgba(0,0,0,.25);
}
.dash-banner-title{font-size:1.6rem;font-weight:700;margin:0}
.dash-banner-sub{font-size:.88rem;opacity:.85;margin:.2rem 0 0}
.kpi-card {
    border-radius:14px;padding:1.2rem 1rem;text-align:center;
    box-shadow:0 6px 20px rgba(0,0,0,.15);transition:transform .2s;
    position:relative;overflow:hidden;
}
.kpi-card:hover{transform:translateY(-3px)}
.kpi-card::after{
    content:'';position:absolute;top:-30%;right:-20%;
    width:80px;height:80px;border-radius:50%;
    background:rgba(255,255,255,.1);
}
.kpi-teal{background:linear-gradient(135deg,#0891b2,#0e7490);color:white}
.kpi-green{background:linear-gradient(135deg,#10b981,#059669);color:white}
.kpi-amber{background:linear-gradient(135deg,#f59e0b,#d97706);color:white}
.kpi-red{background:linear-gradient(135deg,#ef4444,#dc2626);color:white}
.kpi-purple{background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:white}
.kpi-val{font-size:2rem;font-weight:800;line-height:1}
.kpi-lbl{font-size:.74rem;opacity:.9;margin-top:4px;font-weight:500}
.kpi-icon{font-size:1.3rem;margin-bottom:.3rem}

.dash-card {
    background:white;border-radius:14px;padding:1.3rem 1.5rem;
    box-shadow:0 2px 16px rgba(0,0,0,.08);margin-bottom:.9rem;
    border-left:4px solid #0891b2;transition:box-shadow .2s;
}
.dash-card:hover{box-shadow:0 6px 24px rgba(0,0,0,.13)}
.dash-card.green{border-left-color:#10b981}
.dash-card.amber{border-left-color:#f59e0b}
.dash-card.red{border-left-color:#ef4444}
.dash-card.purple{border-left-color:#8b5cf6}

.info-box{background:#e0f2fe;border-left:4px solid #0891b2;border-radius:0 10px 10px 0;padding:.8rem 1rem;margin:.5rem 0}
.warn-box{background:#fef3c7;border-left:4px solid #f59e0b;border-radius:0 10px 10px 0;padding:.8rem 1rem;margin:.5rem 0}
.success-box{background:#d1fae5;border-left:4px solid #10b981;border-radius:0 10px 10px 0;padding:.8rem 1rem;margin:.5rem 0}

.calc-result {
    background:linear-gradient(135deg,#0891b2,#0e7490);border-radius:14px;
    padding:1.5rem;color:white;text-align:center;margin:1rem 0;
}
.calc-val{font-size:2.8rem;font-weight:800}
.calc-lbl{font-size:1rem;opacity:.9;margin-top:.3rem}
.calc-cat{font-size:.85rem;opacity:.8;margin-top:.2rem}

.dir-card {
    background:white;border-radius:12px;padding:1rem 1.2rem;
    box-shadow:0 2px 12px rgba(0,0,0,.07);margin-bottom:.6rem;
    display:flex;align-items:center;gap:1rem;
    border:1px solid #f0f0f0;transition:box-shadow .2s;
}
.dir-card:hover{box-shadow:0 4px 20px rgba(0,0,0,.12)}
.dir-avatar {
    width:48px;height:48px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-size:1.4rem;flex-shrink:0;
}

.nota-card {
    border-radius:12px;padding:1rem 1.2rem;margin-bottom:.8rem;
    position:relative;box-shadow:0 3px 12px rgba(0,0,0,.1);
}
.nota-amarilla{background:linear-gradient(135deg,#fef3c7,#fde68a);border-left:4px solid #f59e0b}
.nota-azul{background:linear-gradient(135deg,#dbeafe,#bfdbfe);border-left:4px solid #3b82f6}
.nota-verde{background:linear-gradient(135deg,#d1fae5,#a7f3d0);border-left:4px solid #10b981}
.nota-roja{background:linear-gradient(135deg,#fee2e2,#fecaca);border-left:4px solid #ef4444}

[data-testid="stSidebar"]{background:linear-gradient(180deg,#061a2e,#0d3d5e) !important}
[data-testid="stSidebar"] *{color:white !important}
[data-testid="stSidebar"] .stButton button{
    background:rgba(255,255,255,.12) !important;color:white !important;
    border:1px solid rgba(255,255,255,.2) !important;border-radius:8px !important;
}
[data-testid="stSidebar"] .stButton button:hover{background:rgba(255,255,255,.22) !important}

.stTabs [data-baseweb="tab-list"]{gap:.4rem}
.stTabs [data-baseweb="tab"]{
    border-radius:10px 10px 0 0;font-weight:600;
    background:rgba(8,145,178,.1);color:#0891b2;
}
.stTabs [aria-selected="true"]{background:#0891b2 !important;color:white !important}

.web-card {
    background:linear-gradient(135deg,#0d4f6c,#065f46);border-radius:14px;
    padding:1.3rem;color:white;height:100%;
    transition:transform .25s,box-shadow .25s;
}
.web-card:hover{transform:translateY(-5px);box-shadow:0 16px 36px rgba(0,0,0,.3)}

.quick-btn {
    display:inline-block;background:linear-gradient(135deg,#0891b2,#0e7490);
    color:white !important;padding:8px 18px;border-radius:20px;
    text-decoration:none;font-size:.85rem;font-weight:600;margin:4px;
    box-shadow:0 4px 14px rgba(8,145,178,.35);transition:transform .2s;
}
.quick-btn:hover{transform:scale(1.05)}

.recov-box {
    background:linear-gradient(135deg,rgba(250,204,21,.15),rgba(245,158,11,.1));
    border:2px solid rgba(250,204,21,.4);border-radius:16px;
    padding:1.5rem;text-align:center;color:white;margin:1rem 0;
}
.recov-code{font-size:3rem;font-weight:800;letter-spacing:.4rem;color:#fde047}
</style>
""", unsafe_allow_html=True)

# ─── DB ──────────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "consultorio.db")

@st.cache_resource
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS pacientes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, telefono TEXT, email TEXT, fecha_nac TEXT,
        sexo TEXT DEFAULT 'No especificado', direccion TEXT,
        alergias TEXT, antecedentes TEXT, medicamentos TEXT,
        tipo_sangre TEXT, notas TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS citas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER, fecha TEXT, motivo TEXT DEFAULT 'Consulta general',
        status TEXT DEFAULT 'PENDIENTE', notas TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(paciente_id) REFERENCES pacientes(id)
    );
    CREATE TABLE IF NOT EXISTS consultas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER, cita_id INTEGER, fecha TEXT,
        motivo TEXT, sintomas TEXT, diagnostico TEXT,
        tratamiento TEXT, receta TEXT,
        tension TEXT, peso REAL, talla REAL, temperatura REAL,
        glucosa REAL, spo2 REAL, observaciones TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(paciente_id) REFERENCES pacientes(id)
    );
    CREATE TABLE IF NOT EXISTS cobros(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER, consulta_id INTEGER,
        concepto TEXT DEFAULT 'Consulta médica',
        monto REAL DEFAULT 500, pagado INTEGER DEFAULT 0,
        metodo_pago TEXT, fecha TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY(paciente_id) REFERENCES pacientes(id)
    );
    CREATE TABLE IF NOT EXISTS inventario(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, categoria TEXT DEFAULT 'Medicamento',
        cantidad INTEGER DEFAULT 0, unidad TEXT DEFAULT 'piezas',
        minimo INTEGER DEFAULT 5, precio REAL, proveedor TEXT,
        vencimiento TEXT, notas TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS prospectos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, email TEXT, especialidad TEXT, telefono TEXT,
        mensaje TEXT, status TEXT DEFAULT 'NUEVO',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, email TEXT UNIQUE, usuario TEXT UNIQUE,
        password TEXT, licencia TEXT, activo INTEGER DEFAULT 0,
        plan TEXT DEFAULT 'Básico', rol TEXT DEFAULT 'doctor',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS directorio(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, telefono TEXT, email TEXT,
        categoria TEXT DEFAULT 'Amigo', direccion TEXT,
        notas TEXT, favorito INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS notas_rapidas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT, contenido TEXT,
        color TEXT DEFAULT 'amarilla',
        fijada INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS recovery_codes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT, code TEXT, expires_at TEXT,
        used INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS secretarias(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        doctor_id INTEGER,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    conn.commit()
    for _migration in [
        "ALTER TABLE usuarios ADD COLUMN rol TEXT DEFAULT 'doctor'",
        "ALTER TABLE usuarios ADD COLUMN citas_max INTEGER DEFAULT 50",
        "ALTER TABLE usuarios ADD COLUMN reportes INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(_migration)
            conn.commit()
        except Exception:
            pass
    return conn

db = init_db()

def qry(sql, params=()):
    cur = db.execute(sql, params); db.commit(); return cur

def rows(sql, params=()):
    return [dict(r) for r in db.execute(sql, params).fetchall()]

def one(sql, params=()):
    r = db.execute(sql, params).fetchone(); return dict(r) if r else None

# ─── EMAIL ───────────────────────────────────────────────────────────────────
def send_email(to_addr, subject, body_html):
    if not SMTP_USER or not SMTP_PASS:
        return False, "SMTP no configurado"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_USER
        msg["To"]      = to_addr
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, to_addr, msg.as_string())
        return True, "Email enviado"
    except Exception as e:
        return False, str(e)

def email_solicitud(nombre, especialidad, telefono, email, mensaje):
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:auto;
                background:linear-gradient(135deg,#0d4f6c,#064e3b);padding:2rem;border-radius:16px;color:white">
        <h2 style="margin:0 0 1rem">🏥 Nueva Solicitud de Alta — MedPanel Pro</h2>
        <div style="background:rgba(255,255,255,.1);border-radius:12px;padding:1.2rem;margin-bottom:1rem">
            <p><b>Nombre:</b> {nombre}</p>
            <p><b>Especialidad:</b> {especialidad}</p>
            <p><b>Teléfono:</b> {telefono}</p>
            <p><b>Email:</b> {email}</p>
            <p><b>Mensaje:</b> {mensaje or '—'}</p>
        </div>
        <p style="font-size:.85rem;opacity:.7">MedPanel Pro · {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>"""
    return send_email(SMTP_USER or ADMIN_EMAIL or email, f"Nueva solicitud: {nombre}", html)

def email_bienvenida(nombre, email_dest):
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:auto">
        <div style="background:linear-gradient(135deg,#0d4f6c,#064e3b);padding:2rem;border-radius:16px 16px 0 0;color:white;text-align:center">
            <div style="font-size:3rem">🏥</div>
            <h1 style="margin:.5rem 0">¡Bienvenido a MedPanel Pro!</h1>
            <p style="opacity:.85">Dr(a). {nombre}</p>
        </div>
        <div style="background:#f9fafb;padding:2rem;border-radius:0 0 16px 16px">
            <p>Gracias por tu interés en <b>MedPanel Pro</b>. Nuestro equipo se pondrá en contacto contigo en menos de <b>24 horas</b> para activar tu cuenta.</p>
            <h3 style="color:#0e7490">Nuestros planes:</h3>
            <table style="width:100%;border-collapse:collapse">
                <tr style="background:#0e7490;color:white">
                    <th style="padding:10px">Plan</th><th style="padding:10px">Precio/mes</th><th style="padding:10px">Incluye</th>
                </tr>
                <tr style="background:#f0fdfa">
                    <td style="padding:10px;font-weight:700">🌱 Básico</td>
                    <td style="padding:10px;text-align:center">$299</td>
                    <td style="padding:10px">Agenda, Pacientes, Recetas PDF</td>
                </tr>
                <tr style="background:white">
                    <td style="padding:10px;font-weight:700">⭐ Profesional</td>
                    <td style="padding:10px;text-align:center">$599</td>
                    <td style="padding:10px">Todo + Inventario, Estadísticas, Calculadoras</td>
                </tr>
                <tr style="background:#f0fdfa">
                    <td style="padding:10px;font-weight:700">🏥 Clínica</td>
                    <td style="padding:10px;text-align:center">$999</td>
                    <td style="padding:10px">Todo + Multi-usuario, Soporte prioritario 24/7</td>
                </tr>
            </table>
            <p style="margin-top:1.5rem;font-size:.85rem;color:#6b7280">
                ¿Tienes preguntas? Escríbenos a {SMTP_USER or 'soporte@medpanelpro.com'}
            </p>
        </div>
    </div>"""
    return send_email(email_dest, "¡Bienvenido a MedPanel Pro! 🏥", html)

def email_recovery(email_dest, code):
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:500px;margin:auto">
        <div style="background:linear-gradient(135deg,#0d4f6c,#064e3b);padding:2rem;border-radius:16px;color:white;text-align:center">
            <div style="font-size:2.5rem">🔐</div>
            <h2>Código de recuperación</h2>
            <p style="opacity:.85">Tu código de acceso temporal:</p>
            <div style="background:rgba(255,255,255,.15);border-radius:12px;padding:1.5rem;
                        font-size:2.5rem;font-weight:800;letter-spacing:.5rem;font-family:monospace">
                {code}
            </div>
            <p style="font-size:.8rem;opacity:.7;margin-top:1rem">
                Este código expira en 15 minutos. Si no solicitaste esto, ignora este mensaje.
            </p>
        </div>
    </div>"""
    return send_email(email_dest, "Código de recuperación — MedPanel Pro", html)

# ─── RECETA PDF ───────────────────────────────────────────────────────────────
def generar_receta_pdf(paciente, diagnostico, receta_texto):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            topMargin=.6*inch, bottomMargin=.6*inch,
                            leftMargin=.8*inch, rightMargin=.8*inch)
    sty = getSampleStyleSheet()
    el = []
    hdr = Table([[
        Paragraph(f"<b>{CLINIC_NAME}</b>", sty['Title']),
        Paragraph(f"<b>{DOCTOR_NAME}</b><br/><font size='9'>{SPECIALTY}</font>", sty['Normal'])
    ]], colWidths=[3.5*inch, 3.5*inch])
    hdr.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#0e7490')),
        ('TEXTCOLOR',(0,0),(-1,-1),colors.white),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('PADDING',(0,0),(-1,-1),12),
    ]))
    el.append(hdr); el.append(Spacer(1,.3*inch))
    el.append(Paragraph(
        f"<b>Paciente:</b> {paciente}   "
        f"<b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}", sty['Normal']))
    el.append(Spacer(1,.1*inch))
    el.append(Paragraph(f"<b>Diagnostico:</b> {diagnostico or '--'}", sty['Normal']))
    el.append(Spacer(1,.15*inch))
    el.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0e7490')))
    el.append(Spacer(1,.15*inch))
    el.append(Paragraph("<font size='18' color='#0e7490'><b>Rx</b></font>", sty['Normal']))
    el.append(Spacer(1,.1*inch))
    for linea in receta_texto.strip().split('\n'):
        if linea.strip():
            el.append(Paragraph(f"• {linea.strip()}", sty['Normal']))
            el.append(Spacer(1,.04*inch))
    el.append(Spacer(1,.5*inch))
    el.append(HRFlowable(width="3*inch", thickness=.5, color=colors.grey))
    el.append(Paragraph(f"Firma: {DOCTOR_NAME}", sty['Normal']))
    el.append(Spacer(1,.08*inch))
    el.append(Paragraph(
        "<font size='7' color='grey'>Generado con MedPanel Pro — Solo valido con sello y firma</font>",
        sty['Normal']))
    doc.build(el)
    buf.seek(0)
    return buf

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for k, v in [('logged_in', False), ('show_recov_code', None), ('recov_verified', False), ('rol', 'doctor')]:
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
#  LANDING PAGE (PRE-LOGIN)
# ══════════════════════════════════════════════════════════════════════════════
# ─── PAYMENT HANDLER ─────────────────────────────────────────────────────────
PLAN_LIMITES = {
    "Básico": {"citas_max": 50,  "reportes": 0},
    "Pro":    {"citas_max": 500, "reportes": 1},
}

def aplicar_permisos_plan(user_id, plan):
    lim = PLAN_LIMITES.get(plan, PLAN_LIMITES["Básico"])
    qry("UPDATE usuarios SET citas_max=?, reportes=? WHERE id=?",
        (lim["citas_max"], lim["reportes"], user_id))

def mostrar_logout_tab():
    st.markdown("### 🚪 Cerrar Sesión")
    if st.button("Cerrar Sesión", key="logout_tab", type="primary"):
        st.session_state.clear()
        st.rerun()

def _gen_pass(n=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def _enviar_credenciales(email, usuario, password):
    if not SMTP_USER or not SMTP_PASS:
        return
    msg = MIMEMultipart()
    msg["From"]    = SMTP_USER
    msg["To"]      = email
    msg["Subject"] = "✅ Tu acceso a ConsultorioBot"
    cuerpo = f"""
    <h2>¡Bienvenido a MedPanel Pro!</h2>
    <p>Tu pago fue aprobado. Aquí están tus credenciales:</p>
    <ul>
      <li><b>Usuario:</b> {usuario}</li>
      <li><b>Contraseña:</b> {password}</li>
    </ul>
    <p>Entra en: <a href="{_s('APP_URL','')}">Abrir App</a></p>
    <p style="color:#888;font-size:12px">Por seguridad, cambia tu contraseña al ingresar.</p>
    """
    msg.attach(MIMEText(cuerpo, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as srv:
            srv.starttls()
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_USER, email, msg.as_string())
    except Exception as e:
        st.warning(f"Email no enviado: {e}")

_qp = st.query_params
if _qp.get("payment_id") and MP_TOKEN:
    import mercadopago, uuid, bcrypt
    _sdk  = mercadopago.SDK(MP_TOKEN)
    _pay  = _sdk.payment().get(_qp["payment_id"])
    _resp = _pay.get("response", {})
    _status = _resp.get("status", "")
    _ref    = _resp.get("external_reference", "")
    if _status == "approved" and _ref:
        # Tarea 2: activar usuario pendiente creado en el form
        _pro = one("SELECT nombre, mensaje FROM prospectos WHERE email=? ORDER BY id DESC LIMIT 1", (_ref,))
        _exist = db.execute("SELECT id, usuario FROM usuarios WHERE email=?", (_ref,)).fetchone()
        _raw_pass = _gen_pass()
        _hash = bcrypt.hashpw(_raw_pass.encode(), bcrypt.gensalt()).decode()
        _lic  = str(uuid.uuid4())
        if _exist and _exist["usuario"]:
            # Usuario ya tiene nombre de usuario asignado (creado por admin)
            _usuario = _exist["usuario"]
        else:
            _nombre  = (_pro[0] if _pro else _ref.split("@")[0]).replace(" ","").lower()
            _usuario = f"dr{_nombre[:8]}{random.randint(100,999)}"
        _msg     = (_pro[1] if _pro and _pro[1] else "").lower()
        _plan_wh = "Pro" if "pro" in _msg else "Básico"
        # UPDATE: activa cuenta, asigna licencia y password
        qry("""UPDATE usuarios
               SET activo=1, licencia=?, password=?, usuario=COALESCE(NULLIF(usuario,''),?),
                   plan=COALESCE(NULLIF(plan,''),?)
               WHERE email=?""",
            (_lic, _hash, _usuario, _plan_wh, _ref))
        # Si no existía, inserta
        qry("""INSERT OR IGNORE INTO usuarios(nombre,email,usuario,password,licencia,activo,plan,created_at)
               VALUES(?,?,?,?,?,1,?,(SELECT datetime('now')))""",
            (_pro[0] if _pro else _ref, _ref, _usuario, _hash, _lic, _plan_wh))
        _new_uid = db.execute("SELECT id FROM usuarios WHERE email=?", (_ref,)).fetchone()
        if _new_uid:
            aplicar_permisos_plan(_new_uid["id"], _plan_wh)
        qry("UPDATE prospectos SET mensaje=REPLACE(mensaje,'pendiente','pagado') WHERE email=?", (_ref,))
        _enviar_credenciales(_ref, _usuario, _raw_pass)
        st.success("✅ Pago aprobado. Revisa tu correo para recibir tus accesos.")
        st.query_params.clear()
    elif _status:
        st.warning(f"Estado del pago: {_status}. Contacta soporte si hay dudas.")

if not st.session_state.logged_in:

    # ── HERO ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-wrap">
        <div style="text-align:center;position:relative;z-index:1">
            <div style="font-size:5rem;animation:float 3s ease infinite">🏥</div>
            <div class="hero-title">MedPanel Pro</div>
            <div class="hero-subtitle">
                El sistema de gestión médica más completo para tu consultorio.<br>
                Diseñado por y para médicos mexicanos.
            </div>
            <div style="margin-top:1.2rem">
                <span class="hero-badge">✅ Agenda digital</span>
                <span class="hero-badge">📋 Expedientes SOAP</span>
                <span class="hero-badge">💊 Recetas PDF</span>
                <span class="hero-badge">📊 Estadísticas</span>
                <span class="hero-badge">🧮 Calculadoras médicas</span>
                <span class="hero-badge">📞 Directorio personal</span>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;
                    margin-top:2rem;position:relative;z-index:1">
            <div class="feature-card">
                <div class="feature-icon">📅</div>
                <div class="feature-title">Agenda Inteligente</div>
                <div class="feature-desc">Gestiona citas, recordatorios y estados en tiempo real</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🩺</div>
                <div class="feature-title">Expedientes SOAP</div>
                <div class="feature-desc">Consultas completas con signos vitales y diagnósticos</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🧮</div>
                <div class="feature-title">Calculadoras Clínicas</div>
                <div class="feature-desc">IMC, clearance renal, dosis pediátricas y más</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── TABS DE ACCESO ────────────────────────────────────────────────────────
    lt1, lt2, lt3, lt4 = st.tabs([
        "🔐 Iniciar Sesión", "📝 Solicitar Alta", "ℹ️ Información", "🔑 Recuperar Contraseña"
    ])

    # ── TAB LOGIN ─────────────────────────────────────────────────────────────
    with lt1:
        _, lc, _ = st.columns([1, 1.5, 1])
        with lc:
            st.markdown('<div class="glass-login">', unsafe_allow_html=True)
            st.markdown('<div class="login-logo">🔐</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-title">Acceso al Panel</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-sub">Ingresa tus credenciales para continuar</div>', unsafe_allow_html=True)
            user = st.text_input("👤 Usuario", placeholder="admin", key="login_user")
            pwd  = st.text_input("🔒 Contraseña", type="password", key="login_pwd")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("→ Entrar al Panel", type="primary", use_container_width=True, key="btn_login"):
                if user == ADMIN_USER and pwd == ADMIN_PASS:
                    st.session_state.logged_in = True
                    st.session_state.rol = "admin"
                    st.session_state.plan = "Clínica"
                    st.rerun()
                else:
                    import bcrypt as _bcrypt
                    _u = one("SELECT id,nombre,password,plan,activo,rol FROM usuarios WHERE usuario=? LIMIT 1", (user,))
                    if _u and _u["activo"] and _bcrypt.checkpw(pwd.encode(), _u["password"].encode()):
                        st.session_state.logged_in = True
                        st.session_state.rol  = _u["rol"] or "doctor"
                        st.session_state.plan = _u["plan"] or "Básico"
                        st.session_state.user_id = _u["id"]
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos")
            st.markdown('<div style="text-align:center;margin-top:.8rem;font-size:.8rem;color:rgba(255,255,255,.6)">'
                        '¿No tienes cuenta? Usa la pestaña <b>Solicitar Alta</b></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── TAB SOLICITAR ALTA ────────────────────────────────────────────────────
    with lt2:
        st.markdown("### 📝 Solicitar acceso a MedPanel Pro")
        st.markdown('<div class="info-box">Completa el formulario y recibirás información de precios en tu correo.</div>',
                    unsafe_allow_html=True)
        with st.form("form_solicitud"):
            sa1, sa2 = st.columns(2)
            with sa1:
                s_nombre = st.text_input("Nombre completo *")
                s_email  = st.text_input("Correo electrónico *")
            with sa2:
                s_esp   = st.selectbox("Especialidad *", [
                    "Medicina General", "Pediatría", "Ginecología", "Cardiología",
                    "Dermatología", "Ortopedia", "Neurología", "Oftalmología",
                    "Odontología", "Psiquiatría", "Endocrinología", "Otra"
                ])
                s_tel   = st.text_input("Teléfono")
            s_plan = st.selectbox("Plan *", ["Básico — $299/mes", "Profesional — $599/mes", "Clínica — $999/mes"])
            s_msj = st.text_area("¿Algo que quieras contarnos?", height=80)
            submitted = st.form_submit_button("💳 Continuar al Pago", type="primary")

        if submitted:
            if s_nombre and s_email:
                precios = {"Básico — $299/mes": 299, "Profesional — $599/mes": 599, "Clínica — $999/mes": 999}
                monto       = precios[s_plan]
                nombre_plan = s_plan.split("—")[0].strip()
                # Tarea 1: INSERT pendiente (sin licencia ni password aún)
                qry("""INSERT OR IGNORE INTO usuarios(nombre,email,plan,activo,created_at)
                       VALUES(?,?,?,0,(SELECT datetime('now')))""",
                    (s_nombre, s_email, nombre_plan))
                qry("UPDATE usuarios SET nombre=?,plan=? WHERE email=? AND activo=0",
                    (s_nombre, nombre_plan, s_email))
                qry("INSERT INTO prospectos(nombre,email,especialidad,telefono,mensaje) VALUES(?,?,?,?,?)",
                    (s_nombre, s_email, s_esp, s_tel, f"[{s_plan}] {s_msj}"))
                if MP_TOKEN:
                    import mercadopago
                    sdk  = mercadopago.SDK(MP_TOKEN)
                    pref = sdk.preference().create({
                        "items": [{"title": f"MedPanel Pro — {nombre_plan}", "quantity": 1,
                                   "currency_id": "MXN", "unit_price": float(monto)}],
                        "payer": {"email": s_email, "name": s_nombre},
                        "back_urls": {"success": _s("APP_URL","") + "?payment_id={preference_id}",
                                      "failure": _s("APP_URL","") + "?paid=failure"},
                        "auto_return": "approved",
                        "external_reference": s_email,
                    })
                    link = pref["response"].get("init_point", "")
                    if link:
                        st.link_button(f"💳 Pagar {nombre_plan} ${monto}/mes", link, type="primary")
                        st.warning("⚠️ Completa el pago para activar tu cuenta. Recibirás tus credenciales por correo.")
                    else:
                        st.error("Error al crear preferencia MP. Contacta soporte.")
                else:
                    email_solicitud(s_nombre, s_esp, s_tel, s_email, s_msj)
                    st.success(f"✅ ¡Gracias, {s_nombre.split()[0]}! Te contactaremos en menos de 24 horas.")
                    st.balloons()
            else:
                st.warning("Nombre y correo son obligatorios")

        st.markdown("---")
        st.markdown("### 💳 Nuestros Planes")
        p1, p2, p3 = st.columns(3)
        with p1:
            st.markdown("""
            <div class="price-card">
                <div class="price-badge">🌱 BÁSICO</div>
                <div class="price-amount">$299</div>
                <div class="price-period">/ mes (MXN)</div>
                <hr style="border-color:rgba(255,255,255,.2);margin:1rem 0">
                <div class="price-feature">✅ Agenda de citas</div>
                <div class="price-feature">✅ Expedientes de pacientes</div>
                <div class="price-feature">✅ Recetas en PDF</div>
                <div class="price-feature">✅ Cobros y pagos</div>
                <div class="price-feature">❌ Estadísticas</div>
                <div class="price-feature">❌ Calculadoras médicas</div>
            </div>""", unsafe_allow_html=True)
        with p2:
            st.markdown("""
            <div class="price-card featured">
                <div class="price-badge">⭐ MÁS POPULAR</div>
                <div class="price-amount">$599</div>
                <div class="price-period">/ mes (MXN)</div>
                <hr style="border-color:rgba(255,255,255,.2);margin:1rem 0">
                <div class="price-feature">✅ Todo el plan Básico</div>
                <div class="price-feature">✅ Inventario de medicamentos</div>
                <div class="price-feature">✅ Estadísticas y gráficas</div>
                <div class="price-feature">✅ Calculadoras clínicas</div>
                <div class="price-feature">✅ Directorio personal</div>
                <div class="price-feature">✅ Notas rápidas</div>
            </div>""", unsafe_allow_html=True)
        with p3:
            st.markdown("""
            <div class="price-card">
                <div class="price-badge">🏥 CLÍNICA</div>
                <div class="price-amount">$999</div>
                <div class="price-period">/ mes (MXN)</div>
                <hr style="border-color:rgba(255,255,255,.2);margin:1rem 0">
                <div class="price-feature">✅ Todo el plan Profesional</div>
                <div class="price-feature">✅ Multi-usuario</div>
                <div class="price-feature">✅ Soporte prioritario 24/7</div>
                <div class="price-feature">✅ Configuración personalizada</div>
                <div class="price-feature">✅ Capacitación incluida</div>
                <div class="price-feature">✅ Respaldo diario</div>
            </div>""", unsafe_allow_html=True)

    # ── TAB INFORMACIÓN ───────────────────────────────────────────────────────
    with lt3:
        st.markdown("### ℹ️ ¿Qué es MedPanel Pro?")
        st.markdown("""
        **MedPanel Pro** es el sistema de gestión médica diseñado específicamente para consultorios
        y clínicas en México. Centraliza todo lo que necesitas para operar tu consultorio de forma
        eficiente, profesional y sin complicaciones.
        """)

        inf1, inf2 = st.columns(2)
        with inf1:
            for feat, desc in [
                ("📅 Agenda Inteligente", "Gestiona citas con estados (pendiente/confirmada/cancelada), notas y visualización por fecha."),
                ("👥 Expedientes Digitales", "Historial completo de cada paciente: alergias, antecedentes, tipo de sangre, consultas previas."),
                ("🩺 Notas SOAP", "Documenta cada consulta con formato médico: Subjetivo, Objetivo, Análisis y Plan."),
                ("💊 Recetas PDF", "Genera recetas profesionales en PDF listas para imprimir o compartir digitalmente."),
                ("💰 Control de Cobros", "Registra pagos, mantén pendientes y genera reportes financieros mensuales."),
            ]:
                st.markdown(f"""
                <div class="info-feature">
                    <b>{feat}</b>
                    <p style="margin:.4rem 0 0;font-size:.9rem;opacity:.85">{desc}</p>
                </div>""", unsafe_allow_html=True)

        with inf2:
            for feat, desc in [
                ("📦 Inventario", "Controla medicamentos y materiales con alertas de stock mínimo y fecha de vencimiento."),
                ("🧮 Calculadoras Clínicas", "IMC, clearance de creatinina, superficie corporal, dosis pediátricas y fecha probable de parto."),
                ("📞 Directorio Personal", "Organiza contactos, colegas, restaurantes y lugares favoritos con acceso rápido."),
                ("📊 Estadísticas", "Visualiza ingresos, diagnósticos frecuentes, nuevos pacientes y más con gráficas interactivas."),
                ("🌐 Recursos Médicos", "Acceso rápido a CIE-10, Vademécum, IMSS, COFEPRIS, Medscape y más."),
            ]:
                st.markdown(f"""
                <div class="info-feature">
                    <b>{feat}</b>
                    <p style="margin:.4rem 0 0;font-size:.9rem;opacity:.85">{desc}</p>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔒 Seguridad y Privacidad")
        st.markdown("""
        - Tus datos se almacenan de forma segura y **nunca se comparten** con terceros.
        - Base de datos dedicada para tu consultorio, sin mezcla de información.
        - Acceso protegido con contraseña.
        - Generado con tecnología de última generación (Python + SQLite + Streamlit Cloud).
        """)

    # ── TAB RECUPERAR CONTRASEÑA ──────────────────────────────────────────────
    with lt4:
        st.markdown("### 🔑 Recuperar Contraseña")
        st.markdown('<div class="info-box">Ingresa tu correo de administrador para recibir un código de verificación.</div>',
                    unsafe_allow_html=True)

        _, rc, _ = st.columns([1, 2, 1])
        with rc:
            if not st.session_state.recov_verified:
                r_email = st.text_input("📧 Correo electrónico registrado")
                if st.button("📨 Enviar código", type="primary", use_container_width=True):
                    if r_email:
                        code = ''.join(random.choices(string.digits, k=6))
                        expires = (datetime.now() + timedelta(minutes=15)).isoformat()
                        qry("INSERT INTO recovery_codes(email,code,expires_at) VALUES(?,?,?)",
                            (r_email, code, expires))
                        sent, msg = email_recovery(r_email, code)
                        if sent:
                            st.session_state.show_recov_code = None
                            st.success("✅ Código enviado a tu correo")
                        else:
                            st.session_state.show_recov_code = code
                            st.warning("⚠️ Email no configurado. Código de demostración:")
                            st.markdown(f"""
                            <div class="recov-box">
                                <div style="font-size:1rem;opacity:.8;margin-bottom:.5rem">Código de verificación</div>
                                <div class="recov-code">{code}</div>
                                <div style="font-size:.8rem;opacity:.6;margin-top:.5rem">Expira en 15 minutos</div>
                            </div>""", unsafe_allow_html=True)
                    else:
                        st.warning("Ingresa tu correo")

                st.markdown("---")
                r_code = st.text_input("🔢 Código de 6 dígitos")
                if st.button("✅ Verificar código", use_container_width=True):
                    if r_code:
                        rec = one("SELECT * FROM recovery_codes WHERE code=? AND used=0 ORDER BY id DESC LIMIT 1",
                                  (r_code,))
                        if rec and datetime.fromisoformat(rec['expires_at']) > datetime.now():
                            qry("UPDATE recovery_codes SET used=1 WHERE id=?", (rec['id'],))
                            st.session_state.recov_verified = True
                            st.rerun()
                        else:
                            st.error("Código inválido o expirado")
                    else:
                        st.warning("Ingresa el código")
            else:
                st.success("✅ Código verificado. Ahora puedes iniciar sesión.")
                st.markdown(f"""
                <div class="recov-box">
                    <div style="font-size:1rem">Tu contraseña actual:</div>
                    <div class="recov-code" style="font-size:1.8rem;letter-spacing:.2rem">{ADMIN_PASS}</div>
                    <div style="font-size:.8rem;opacity:.7;margin-top:.5rem">Ve a la pestaña "Iniciar Sesión"</div>
                </div>""", unsafe_allow_html=True)
                if st.button("🔐 Ir al login"):
                    st.session_state.recov_verified = False
                    st.rerun()

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL PRINCIPAL (POST-LOGIN)
# ══════════════════════════════════════════════════════════════════════════════

# ── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 🏥 {CLINIC_NAME}")
    st.caption(f"👨‍⚕️ {DOCTOR_NAME}")
    st.caption(f"🩺 {SPECIALTY}")
    if PHONE: st.caption(f"📞 {PHONE}")
    st.markdown("---")
    st.caption(f"📅 {date.today().strftime('%A %d/%m/%Y')}")
    st.caption(f"🕐 {datetime.now().strftime('%H:%M')}")
    st.markdown("---")
    st.markdown("**Acciones rápidas**")
    if st.button("➕ Nueva Cita", use_container_width=True):
        st.session_state['show_form_cita'] = True
    if st.button("➕ Nuevo Paciente", use_container_width=True):
        st.session_state['goto_nuevo_pac'] = True
    if st.button("🩺 Nueva Consulta", use_container_width=True):
        st.session_state['goto_nueva_cons'] = True
    st.markdown("---")
    pend_count = one("SELECT COUNT(*) as n FROM cobros WHERE pagado=0")['n'] or 0
    inv_bajo   = one("SELECT COUNT(*) as n FROM inventario WHERE cantidad<=minimo")['n'] or 0
    if pend_count: st.warning(f"💰 {pend_count} cobros pendientes")
    if inv_bajo:   st.warning(f"📦 {inv_bajo} artículos bajos")
    st.markdown("---")
    _sid_rol  = st.session_state.get("rol", "")
    _sid_plan = st.session_state.get("plan", "")
    if _sid_rol:
        st.caption(f"🔑 {_sid_rol.capitalize()} · {_sid_plan}")
    if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        for _k in list(st.session_state.keys()):
            del st.session_state[_k]
        st.rerun()

# ── BANNER ────────────────────────────────────────────────────────────────────
hora  = datetime.now().hour
salud = "Buenos días" if hora < 12 else ("Buenas tardes" if hora < 19 else "Buenas noches")
st.markdown(f"""
<div class="dash-banner">
    <div>
        <div class="dash-banner-title">🏥 {CLINIC_NAME}</div>
        <div class="dash-banner-sub">{salud}, {DOCTOR_NAME} · {SPECIALTY}</div>
    </div>
    <div style="text-align:right;font-size:.9rem;opacity:.85">
        📅 {date.today().strftime('%d de %B de %Y')}<br>
        🕐 {datetime.now().strftime('%H:%M hrs')}
    </div>
</div>""", unsafe_allow_html=True)

# ── KPIs ─────────────────────────────────────────────────────────────────────
try:
    hoy_str      = date.today().isoformat()
    citas_hoy    = rows("SELECT * FROM citas WHERE fecha LIKE ?", (f"{hoy_str}%",))
    pendientes   = rows("SELECT * FROM citas WHERE status='PENDIENTE'")
    total_pacs   = one("SELECT COUNT(*) as n FROM pacientes")['n']
    mes_actual   = datetime.now().strftime('%Y-%m')
    ingresos_mes = one("SELECT COALESCE(SUM(monto),0) as s FROM cobros WHERE pagado=1 AND fecha LIKE ?",
                       (f"{mes_actual}%",))['s']
    por_cobrar   = one("SELECT COALESCE(SUM(monto),0) as s FROM cobros WHERE pagado=0")['s']
    n_notas      = one("SELECT COUNT(*) as n FROM notas_rapidas")['n']
except Exception:
    citas_hoy=[]; pendientes=[]; total_pacs=0; ingresos_mes=0; por_cobrar=0; n_notas=0

k1,k2,k3,k4,k5 = st.columns(5)
k1.markdown(f'<div class="kpi-card kpi-teal"><div class="kpi-icon">📅</div><div class="kpi-val">{len(citas_hoy)}</div><div class="kpi-lbl">Citas hoy</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-card kpi-amber"><div class="kpi-icon">⏳</div><div class="kpi-val">{len(pendientes)}</div><div class="kpi-lbl">Pendientes</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-card kpi-green"><div class="kpi-icon">👥</div><div class="kpi-val">{total_pacs}</div><div class="kpi-lbl">Pacientes</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-card kpi-green"><div class="kpi-icon">💵</div><div class="kpi-val">${ingresos_mes:,.0f}</div><div class="kpi-lbl">Ingresos mes</div></div>', unsafe_allow_html=True)
k5.markdown(f'<div class="kpi-card kpi-red"><div class="kpi-icon">💳</div><div class="kpi-val">${por_cobrar:,.0f}</div><div class="kpi-lbl">Por cobrar</div></div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── PLAN GATE ─────────────────────────────────────────────────────────────────
_PLAN_NIVEL = {"Básico": 1, "Profesional": 2, "Clínica": 3}
_user_plan  = getattr(st.session_state, "plan", "Clínica") if st.session_state.rol == "admin" else st.session_state.get("plan", "Clínica")
_nivel      = _PLAN_NIVEL.get(_user_plan, 3)

def _gate(req: int, nombre: str, upgrade: str):
    """Muestra candado si el plan del usuario no alcanza el nivel requerido."""
    if _nivel < req:
        st.markdown(f"""
<div style="text-align:center;padding:3rem 1rem;border:2px dashed rgba(108,99,255,.4);
border-radius:16px;background:rgba(108,99,255,.05);margin-top:1rem">
  <div style="font-size:3rem">🔒</div>
  <h3 style="margin:.5rem 0">{nombre} no disponible en tu plan</h3>
  <p style="color:#888">Requiere plan <b>{upgrade}</b> o superior.</p>
  <p style="color:#aaa;font-size:.9rem">Escríbenos por WhatsApp para hacer upgrade.</p>
  <a href="https://wa.me/526331124596?text=Quiero%20cambiar%20al%20plan%20{upgrade}"
     target="_blank" style="display:inline-block;margin-top:1rem;padding:.7rem 1.8rem;
     background:linear-gradient(135deg,#6C63FF,#9b5de5);color:#fff;border-radius:10px;
     text-decoration:none;font-weight:700">💬 Hacer Upgrade</a>
</div>""", unsafe_allow_html=True)
        return True
    return False

# ── TABS PRINCIPALES ──────────────────────────────────────────────────────────
_rol = st.session_state.get("rol", "doctor")

if _rol == "secretaria":
    _tab_labels = ["📅 Agenda", "👥 Pacientes"]
    tabs = st.tabs(_tab_labels)
    t_agenda, t_pacs = tabs
    t_cons = t_rec = t_cobros = t_inv = t_calc = t_dir = t_stats = t_webs = t_admin = None
else:
    _tab_labels = ["📅 Agenda", "👥 Pacientes", "🩺 Consultas",
                   "💊 Recetas", "💰 Cobros", "📦 Inventario",
                   "🧮 Calculadoras", "📞 Directorio", "📊 Estadísticas", "🌐 Recursos"]
    if _rol == "doctor":
        _tab_labels.append("🧑‍💼 Mi Secretaria")
    if _rol == "admin":
        _tab_labels.append("👑 Admin")
    _tab_labels.append("🚪 Salir")
    tabs = st.tabs(_tab_labels)
    (t_agenda, t_pacs, t_cons, t_rec,
     t_cobros, t_inv, t_calc, t_dir, t_stats, t_webs) = tabs[:10]
    t_sec   = tabs[10] if _rol == "doctor" else None
    t_admin = tabs[10] if _rol == "admin"  else None
    t_salir = tabs[-1]
    with t_salir:
        mostrar_logout_tab()

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – AGENDA
# ════════════════════════════════════════════════════════════════════════════
with t_agenda:
    st.subheader("📅 Agenda de Citas")
    pac_lista = rows("SELECT id, nombre FROM pacientes ORDER BY nombre")
    pac_opts  = {f"{p['nombre']} (#{p['id']})": p['id'] for p in pac_lista}

    col_fil, col_nueva = st.columns([2, 1])
    with col_fil:
        filtro = st.multiselect("Estado", ["PENDIENTE","CONFIRMADA","CANCELADA"],
                                default=["PENDIENTE","CONFIRMADA"])
    with col_nueva:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Nueva Cita", type="primary", use_container_width=True):
            st.session_state['show_form_cita'] = True

    if st.session_state.get('show_form_cita'):
        with st.form("form_nueva_cita"):
            st.markdown("#### Nueva cita")
            a1, a2 = st.columns(2)
            with a1:
                pac_sel  = st.selectbox("Paciente *", ["— Selecciona —"] + list(pac_opts.keys()))
                motivo   = st.text_input("Motivo", value="Consulta general")
            with a2:
                fecha_c  = st.date_input("Fecha")
                hora_c   = st.time_input("Hora")
                status_c = st.selectbox("Estado", ["PENDIENTE","CONFIRMADA","CANCELADA"])
            notas_c = st.text_area("Notas", height=60)
            sb1, sb2 = st.columns(2)
            with sb1:
                if st.form_submit_button("💾 Guardar", type="primary"):
                    if pac_sel != "— Selecciona —":
                        fdt = f"{fecha_c}T{hora_c.strftime('%H:%M')}"
                        qry("INSERT INTO citas(paciente_id,fecha,motivo,status,notas) VALUES(?,?,?,?,?)",
                            (pac_opts[pac_sel], fdt, motivo, status_c, notas_c))
                        st.success("✅ Cita registrada")
                        st.session_state['show_form_cita'] = False
                        st.rerun()
                    else:
                        st.warning("Selecciona un paciente")
            with sb2:
                if st.form_submit_button("Cancelar"):
                    st.session_state['show_form_cita'] = False; st.rerun()

    ph = ','.join(['?']*len(filtro)) if filtro else "''"
    citas = rows(f"""
        SELECT c.id, p.nombre as paciente, p.telefono, c.fecha, c.motivo, c.status, c.notas
        FROM citas c JOIN pacientes p ON c.paciente_id=p.id
        WHERE c.status IN ({ph}) ORDER BY c.fecha DESC LIMIT 100
    """, tuple(filtro))

    if not citas:
        st.info("No hay citas con esos filtros.")
    else:
        for cita in citas:
            icon = {"CONFIRMADA":"🟢","PENDIENTE":"🟡","CANCELADA":"🔴"}.get(cita['status'],'⚪')
            with st.expander(f"{icon} **{cita['paciente']}** · {cita['fecha'][:16]} · {cita['motivo']}"):
                ec1, ec2, ec3, ec4 = st.columns(4)
                ec1.write(f"**Estado:** {cita['status']}")
                ec2.write(f"**Fecha:** {cita['fecha'][:16]}")
                if cita['telefono']:
                    ec3.markdown(f'<a class="quick-btn" href="https://wa.me/52{cita["telefono"].replace(" ","")}" target="_blank">💬 WhatsApp</a>', unsafe_allow_html=True)
                if cita['notas']: ec4.write(f"**Notas:** {cita['notas']}")
                bc1, bc2, bc3, bc4 = st.columns(4)
                for i, nuevo_st in enumerate(["CONFIRMADA","CANCELADA","PENDIENTE"]):
                    with [bc1,bc2,bc3][i]:
                        if st.button(f"→ {nuevo_st}", key=f"st_{cita['id']}_{nuevo_st}"):
                            qry("UPDATE citas SET status=? WHERE id=?", (nuevo_st, cita['id']))
                            st.rerun()
                with bc4:
                    if st.button("🗑️ Eliminar", key=f"del_cita_{cita['id']}"):
                        qry("DELETE FROM citas WHERE id=?", (cita['id'],))
                        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – PACIENTES
# ════════════════════════════════════════════════════════════════════════════
with t_pacs:
    st.subheader("👥 Expediente de Pacientes")
    pt1, pt2 = st.tabs(["📋 Lista", "➕ Agregar"])

    with pt1:
        buscar_p = st.text_input("🔍 Buscar (nombre, teléfono, email)")
        if buscar_p:
            pacs = rows("SELECT * FROM pacientes WHERE nombre LIKE ? OR telefono LIKE ? OR email LIKE ? ORDER BY nombre",
                       (f'%{buscar_p}%',)*3)
        else:
            pacs = rows("SELECT * FROM pacientes ORDER BY nombre LIMIT 100")
        st.metric("Pacientes encontrados", len(pacs))

        for pac in pacs:
            # Calcular edad si hay fecha de nacimiento
            edad_str = ""
            if pac.get('fecha_nac'):
                try:
                    fn = date.fromisoformat(pac['fecha_nac'])
                    edad = (date.today() - fn).days // 365
                    edad_str = f" · {edad} años"
                except Exception:
                    pass

            with st.expander(f"**{pac['nombre']}**{edad_str} · {pac['telefono'] or '—'} · {pac.get('tipo_sangre') or ''}"):
                p1, p2, p3 = st.columns(3)
                p1.write(f"**Email:** {pac['email'] or '—'}")
                p1.write(f"**Nacimiento:** {pac['fecha_nac'] or '—'}")
                p1.write(f"**Sexo:** {pac['sexo'] or '—'}")
                p2.write(f"**Sangre:** {pac['tipo_sangre'] or '—'}")
                p2.write(f"**Alergias:** {pac['alergias'] or '—'}")
                p3.write(f"**Antecedentes:** {pac['antecedentes'] or '—'}")
                p3.write(f"**Medicamentos:** {pac['medicamentos'] or '—'}")
                if pac['notas']:
                    st.markdown(f'<div class="info-box">📝 {pac["notas"]}</div>', unsafe_allow_html=True)
                if pac['telefono']:
                    st.markdown(f'<a class="quick-btn" href="https://wa.me/52{pac["telefono"].replace(" ","")}" target="_blank">💬 WhatsApp</a>', unsafe_allow_html=True)
                hist = rows("SELECT fecha, diagnostico, motivo FROM consultas WHERE paciente_id=? ORDER BY fecha DESC LIMIT 5",
                            (pac['id'],))
                if hist:
                    st.markdown("**Últimas consultas:**")
                    for h in hist:
                        st.caption(f"• {h['fecha'][:10]} — {h['diagnostico'] or h['motivo']}")
                if st.button("🗑️ Eliminar paciente", key=f"del_pac_{pac['id']}"):
                    qry("DELETE FROM pacientes WHERE id=?", (pac['id'],))
                    st.rerun()

    with pt2:
        with st.form("form_paciente"):
            st.markdown("**Datos del paciente**")
            fp1, fp2, fp3 = st.columns(3)
            with fp1:
                p_nombre = st.text_input("Nombre completo *")
                p_tel    = st.text_input("Teléfono *")
                p_email  = st.text_input("Email")
            with fp2:
                p_nac    = st.date_input("Fecha de nacimiento", value=None)
                p_sexo   = st.selectbox("Sexo", ["No especificado","Masculino","Femenino","Otro"])
                p_sangre = st.selectbox("Tipo de sangre", ["—","A+","A-","B+","B-","AB+","AB-","O+","O-"])
            with fp3:
                p_dir    = st.text_area("Dirección", height=68)
                p_alerg  = st.text_input("Alergias conocidas")
            p_ant   = st.text_area("Antecedentes médicos", height=60)
            p_meds  = st.text_area("Medicamentos actuales", height=60)
            p_notas = st.text_area("Notas adicionales", height=60)
            if st.form_submit_button("💾 Guardar Paciente", type="primary"):
                if p_nombre and p_tel:
                    qry("""INSERT INTO pacientes(nombre,telefono,email,fecha_nac,sexo,
                           tipo_sangre,direccion,alergias,antecedentes,medicamentos,notas)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (p_nombre, p_tel, p_email,
                         str(p_nac) if p_nac else None,
                         p_sexo, p_sangre if p_sangre != "—" else None,
                         p_dir, p_alerg, p_ant, p_meds, p_notas))
                    st.success(f"✅ Paciente {p_nombre} registrado")
                else:
                    st.warning("Nombre y teléfono son obligatorios")

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – CONSULTAS
# ════════════════════════════════════════════════════════════════════════════
if t_cons:
 with t_cons:
    st.subheader("🩺 Consultas Médicas")
    ct1, ct2 = st.tabs(["📋 Ver Consultas", "➕ Nueva Consulta"])

    with ct1:
        consultas = rows("""
            SELECT c.id, p.nombre as paciente, c.fecha, c.motivo,
                   c.diagnostico, c.tratamiento, c.tension, c.peso, c.temperatura, c.spo2
            FROM consultas c JOIN pacientes p ON c.paciente_id=p.id
            ORDER BY c.fecha DESC LIMIT 50
        """)
        if not consultas:
            st.info("Sin consultas registradas.")
        for con in consultas:
            with st.expander(f"**{con['paciente']}** · {(con['fecha'] or '')[:10]} · {con['diagnostico'] or con['motivo']}"):
                v1, v2, v3 = st.columns(3)
                v1.write(f"**Motivo:** {con['motivo']}")
                v1.write(f"**Diagnóstico:** {con['diagnostico'] or '—'}")
                v2.write(f"**Tensión:** {con['tension'] or '—'}")
                v2.write(f"**Peso:** {str(con['peso']) + ' kg' if con['peso'] else '—'}")
                v3.write(f"**Temp:** {str(con['temperatura']) + ' °C' if con['temperatura'] else '—'}")
                v3.write(f"**SpO2:** {str(con['spo2']) + ' %' if con['spo2'] else '—'}")
                if con['tratamiento']:
                    st.write(f"**Tratamiento:** {con['tratamiento']}")

    with ct2:
        pac_todos = rows("SELECT id, nombre FROM pacientes ORDER BY nombre")
        pmap = {f"{p['nombre']} (#{p['id']})": p['id'] for p in pac_todos}
        with st.form("form_consulta"):
            st.markdown("**Nueva Consulta — Formato SOAP**")
            nc1, nc2 = st.columns(2)
            with nc1:
                pac_c    = st.selectbox("Paciente *", ["— Selecciona —"] + list(pmap.keys()))
                motivo_c = st.text_input("Motivo de consulta *", value="Consulta general")
                fecha_con = st.date_input("Fecha")
            with nc2:
                tension  = st.text_input("Tensión arterial (ej: 120/80)")
                peso     = st.number_input("Peso (kg)", 0.0, 300.0, step=0.5)
                talla    = st.number_input("Talla (cm)", 0.0, 250.0, step=0.5)
            nc3, nc4 = st.columns(2)
            with nc3:
                temperatura = st.number_input("Temperatura (°C)", 0.0, 45.0, step=0.1)
                glucosa     = st.number_input("Glucosa (mg/dL)", 0.0, 800.0, step=1.0)
                spo2        = st.number_input("SpO2 (%)", 0.0, 100.0, step=0.5)
            with nc4:
                sintomas = st.text_area("🔵 Subjetivo (S) — Síntomas del paciente", height=90)
            diagnostico = st.text_area("🟡 Análisis (A) — Diagnóstico", height=80)
            tratamiento = st.text_area("🟢 Plan (P) — Tratamiento y seguimiento", height=80)
            receta_c    = st.text_area("💊 Receta / Medicamentos", height=80)
            obs         = st.text_area("📝 Observaciones adicionales", height=60)
            cobrar_auto = st.checkbox("Generar cobro automáticamente", value=True)
            monto_cons  = st.number_input("Monto consulta ($)", value=CONSULTA_PRECIO, step=50.0)
            if st.form_submit_button("💾 Guardar Consulta", type="primary"):
                if pac_c != "— Selecciona —" and motivo_c:
                    pid = pmap[pac_c]
                    fecha_str = str(fecha_con)
                    qry("""INSERT INTO consultas(paciente_id,fecha,motivo,sintomas,diagnostico,
                           tratamiento,receta,tension,peso,talla,temperatura,glucosa,spo2,observaciones)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (pid, fecha_str, motivo_c, sintomas, diagnostico, tratamiento,
                         receta_c, tension,
                         peso or None, talla or None, temperatura or None,
                         glucosa or None, spo2 or None, obs))
                    cons_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                    if cobrar_auto:
                        qry("INSERT INTO cobros(paciente_id,consulta_id,concepto,monto,fecha) VALUES(?,?,?,?,?)",
                            (pid, cons_id, "Consulta médica", monto_cons, fecha_str))
                    st.success("✅ Consulta registrada correctamente")
                    st.rerun()
                else:
                    st.warning("Selecciona paciente y motivo")

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 – RECETAS PDF
# ════════════════════════════════════════════════════════════════════════════
if t_rec:
 with t_rec:
    if _gate(2, "💊 Recetas", "Profesional"): st.stop()
    st.subheader("💊 Generador de Recetas PDF")
    st.markdown('<div class="info-box">Genera recetas médicas profesionales en PDF, listas para imprimir o enviar digitalmente.</div>', unsafe_allow_html=True)

    pac_rec = rows("SELECT id, nombre FROM pacientes ORDER BY nombre")
    prmap = {f"{p['nombre']} (#{p['id']})": p['id'] for p in pac_rec}

    with st.form("form_receta"):
        r1, r2 = st.columns(2)
        with r1:
            pac_r   = st.selectbox("Paciente", ["— Manual —"] + list(prmap.keys()))
            pac_nom = st.text_input("O escribe nombre del paciente")
            edad_r  = st.text_input("Edad")
        with r2:
            diag_r = st.text_area("Diagnóstico", height=80)
        receta_txt = st.text_area("Medicamentos y posología *", height=150,
                                   placeholder="Amoxicilina 500mg — 1 cápsula cada 8 hrs por 7 días\nIbuprofeno 400mg — 1 tableta cada 12 hrs con alimentos")
        if st.form_submit_button("📄 Generar PDF", type="primary"):
            if receta_txt.strip():
                nombre_pac = (pac_nom if pac_nom
                              else (pac_r.split(" (#")[0] if pac_r != "— Manual —" else "Paciente"))
                if edad_r: nombre_pac += f", {edad_r} años"
                pdf = generar_receta_pdf(nombre_pac, diag_r, receta_txt)
                st.success("✅ Receta generada")
                st.download_button("📥 Descargar Receta PDF", pdf,
                                   f"Receta_{nombre_pac.split(',')[0]}_{date.today()}.pdf",
                                   "application/pdf", use_container_width=True, type="primary")
            else:
                st.warning("Escribe los medicamentos")

    st.markdown("---")
    st.markdown("#### Recetas de consultas anteriores")
    cons_rec = rows("""
        SELECT c.id, p.nombre, c.fecha, c.diagnostico, c.receta
        FROM consultas c JOIN pacientes p ON c.paciente_id=p.id
        WHERE c.receta IS NOT NULL AND c.receta != ''
        ORDER BY c.fecha DESC LIMIT 20
    """)
    for cr in cons_rec:
        with st.expander(f"**{cr['nombre']}** · {(cr['fecha'] or '')[:10]}"):
            st.write(f"**Diagnóstico:** {cr['diagnostico'] or '—'}")
            st.write(f"**Receta:** {cr['receta']}")
            if st.button("📄 PDF de esta receta", key=f"pdf_cr_{cr['id']}"):
                pdf2 = generar_receta_pdf(cr['nombre'], cr['diagnostico'], cr['receta'])
                st.download_button("📥 Descargar", pdf2,
                                   f"Receta_{cr['nombre'].split()[0]}_{cr['id']}.pdf",
                                   "application/pdf", key=f"dl_cr_{cr['id']}")

# ════════════════════════════════════════════════════════════════════════════
# TAB 5 – COBROS
# ════════════════════════════════════════════════════════════════════════════
if t_cobros:
 with t_cobros:
    if _gate(2, "💰 Cobros", "Profesional"): st.stop()
    st.subheader("💰 Cobros y Pagos")
    cob1, cob2 = st.columns([2, 1])
    with cob1:
        filtro_cob = st.radio("Ver", ["Todos","Pendientes","Pagados"], horizontal=True)
    with cob2:
        if st.button("➕ Nuevo Cobro", type="primary"):
            st.session_state['show_form_cobro'] = True

    if st.session_state.get('show_form_cobro'):
        pac_cob = rows("SELECT id, nombre FROM pacientes ORDER BY nombre")
        pcmap = {f"{p['nombre']} (#{p['id']})": p['id'] for p in pac_cob}
        with st.form("form_cobro"):
            cc1, cc2 = st.columns(2)
            with cc1:
                pac_cb      = st.selectbox("Paciente *", ["— Selecciona —"] + list(pcmap.keys()))
                concepto_cb = st.text_input("Concepto", value="Consulta médica")
            with cc2:
                monto_cb  = st.number_input("Monto ($)", value=CONSULTA_PRECIO, step=50.0)
                metodo_cb = st.selectbox("Forma de pago", ["Efectivo","Transferencia","Tarjeta débito","Tarjeta crédito","—"])
                pagado_cb = st.checkbox("Ya pagado", value=True)
            fecha_cb = st.date_input("Fecha")
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.form_submit_button("💾 Guardar", type="primary"):
                    if pac_cb != "— Selecciona —":
                        qry("INSERT INTO cobros(paciente_id,concepto,monto,pagado,metodo_pago,fecha) VALUES(?,?,?,?,?,?)",
                            (pcmap[pac_cb], concepto_cb, monto_cb,
                             1 if pagado_cb else 0,
                             metodo_cb if metodo_cb != "—" else None, str(fecha_cb)))
                        st.success("✅ Cobro registrado")
                        st.session_state['show_form_cobro'] = False
                        st.rerun()
            with sc2:
                if st.form_submit_button("Cancelar"):
                    st.session_state['show_form_cobro'] = False; st.rerun()

    where_cob = "" if filtro_cob=="Todos" else f" AND cobros.pagado={'1' if filtro_cob=='Pagados' else '0'}"
    cobros = rows(f"""
        SELECT cobros.id, pacientes.nombre as paciente, cobros.concepto,
               cobros.monto, cobros.pagado, cobros.metodo_pago, cobros.fecha
        FROM cobros JOIN pacientes ON cobros.paciente_id=pacientes.id
        WHERE 1=1{where_cob} ORDER BY cobros.fecha DESC LIMIT 100
    """)

    total_cobros = sum(c['monto'] for c in cobros)
    total_pagado = sum(c['monto'] for c in cobros if c['pagado'])
    total_pend   = total_cobros - total_pagado

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Total", f"${total_cobros:,.2f}")
    mc2.metric("Cobrado", f"${total_pagado:,.2f}")
    mc3.metric("Por cobrar", f"${total_pend:,.2f}")

    if cobros:
        df_cob = pd.DataFrame(cobros)
        df_cob['Estado'] = df_cob['pagado'].apply(lambda x: '✅ Pagado' if x else '⏳ Pendiente')
        df_cob['monto']  = df_cob['monto'].apply(lambda x: f"${x:,.2f}")
        st.dataframe(df_cob[['paciente','concepto','monto','Estado','metodo_pago','fecha']],
                     use_container_width=True, hide_index=True)
        for cob in [c for c in cobros if not c['pagado']]:
            if st.button(f"✅ Marcar pagado — {cob['paciente']} ${cob['monto']:.0f}",
                         key=f"pagar_{cob['id']}"):
                qry("UPDATE cobros SET pagado=1 WHERE id=?", (cob['id'],))
                st.rerun()
    else:
        st.info("Sin cobros con ese filtro.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 6 – INVENTARIO
# ════════════════════════════════════════════════════════════════════════════
if t_inv:
 with t_inv:
    if _gate(2, "📦 Inventario", "Profesional"): st.stop()
    st.subheader("📦 Inventario de Medicamentos y Materiales")
    inv1, inv2 = st.tabs(["📋 Stock actual", "➕ Agregar"])

    with inv1:
        inventario = rows("SELECT * FROM inventario ORDER BY categoria, nombre")
        bajos = [i for i in inventario if i['cantidad'] <= i['minimo']]
        if bajos:
            st.markdown(f'<div class="warn-box">⚠️ <b>{len(bajos)} artículos</b> por debajo del mínimo: {", ".join(b["nombre"] for b in bajos)}</div>', unsafe_allow_html=True)
        if not inventario:
            st.info("Inventario vacío.")
        else:
            df_inv = pd.DataFrame(inventario)
            df_inv['Alerta'] = df_inv.apply(lambda r: '🔴 BAJO' if r['cantidad'] <= r['minimo'] else '🟢 OK', axis=1)
            st.dataframe(df_inv[['nombre','categoria','cantidad','unidad','minimo','Alerta','proveedor','vencimiento']],
                         use_container_width=True, hide_index=True)
            st.markdown("---")
            for item in inventario:
                with st.expander(f"{'🔴' if item['cantidad']<=item['minimo'] else '🟢'} **{item['nombre']}** — {item['cantidad']} {item['unidad']}"):
                    i1, i2, i3 = st.columns(3)
                    i1.write(f"**Categoría:** {item['categoria']}")
                    i2.write(f"**Precio:** ${item['precio'] or 0:,.2f}")
                    i3.write(f"**Vencimiento:** {item['vencimiento'] or '—'}")
                    nuevo_qty = st.number_input("Actualizar cantidad", value=int(item['cantidad']),
                                               step=1, key=f"qty_{item['id']}")
                    if st.button("Actualizar", key=f"upd_inv_{item['id']}"):
                        qry("UPDATE inventario SET cantidad=? WHERE id=?", (nuevo_qty, item['id']))
                        st.rerun()

    with inv2:
        with st.form("form_inventario"):
            ii1, ii2, ii3 = st.columns(3)
            with ii1:
                inv_nom  = st.text_input("Nombre del artículo *")
                inv_cat  = st.selectbox("Categoría", ["Medicamento","Material","Equipo","Insumo","Otro"])
                inv_prov = st.text_input("Proveedor")
            with ii2:
                inv_qty  = st.number_input("Cantidad inicial", min_value=0, step=1)
                inv_uni  = st.text_input("Unidad", value="piezas")
                inv_min  = st.number_input("Mínimo", min_value=0, value=5, step=1)
            with ii3:
                inv_precio = st.number_input("Precio unitario ($)", min_value=0.0, step=1.0)
                inv_venc   = st.date_input("Vencimiento", value=None)
                inv_notas  = st.text_area("Notas", height=60)
            if st.form_submit_button("💾 Guardar", type="primary"):
                if inv_nom:
                    qry("""INSERT INTO inventario(nombre,categoria,cantidad,unidad,minimo,precio,proveedor,vencimiento,notas)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (inv_nom, inv_cat, inv_qty, inv_uni, inv_min,
                         inv_precio or None, inv_prov or None,
                         str(inv_venc) if inv_venc else None, inv_notas or None))
                    st.success(f"✅ {inv_nom} agregado")
                    st.rerun()
                else:
                    st.warning("El nombre es obligatorio")

# ════════════════════════════════════════════════════════════════════════════
# TAB 7 – CALCULADORAS MÉDICAS
# ════════════════════════════════════════════════════════════════════════════
if t_calc:
 with t_calc:
    st.subheader("🧮 Calculadoras Clínicas")
    st.markdown('<div class="info-box">Herramientas de apoyo clínico para cálculos médicos frecuentes.</div>', unsafe_allow_html=True)

    cal1, cal2, cal3 = st.tabs(["⚖️ IMC & Superficie", "🧪 Renal & Metabólico", "👶 Pediatría & Obstetricia"])

    with cal1:
        c1a, c1b = st.columns(2)
        with c1a:
            st.markdown("#### ⚖️ Índice de Masa Corporal (IMC)")
            imc_peso = st.number_input("Peso (kg)", 1.0, 300.0, 70.0, step=0.5, key="imc_p")
            imc_tall = st.number_input("Talla (cm)", 50.0, 250.0, 170.0, step=0.5, key="imc_t")
            if imc_peso > 0 and imc_tall > 0:
                imc = imc_peso / ((imc_tall / 100) ** 2)
                if imc < 18.5:       cat, color = "Bajo peso", "#3b82f6"
                elif imc < 25:       cat, color = "Peso normal ✅", "#10b981"
                elif imc < 30:       cat, color = "Sobrepeso", "#f59e0b"
                elif imc < 35:       cat, color = "Obesidad I", "#ef4444"
                elif imc < 40:       cat, color = "Obesidad II", "#dc2626"
                else:                cat, color = "Obesidad III (mórbida)", "#991b1b"
                st.markdown(f"""
                <div class="calc-result" style="background:linear-gradient(135deg,{color},{color}cc)">
                    <div class="calc-val">{imc:.1f}</div>
                    <div class="calc-lbl">kg/m²</div>
                    <div class="calc-cat">{cat}</div>
                </div>""", unsafe_allow_html=True)

                # Peso ideal Devine
                if imc_tall >= 152:
                    if st.checkbox("Ver peso ideal (fórmula Devine)", key="pi_chk"):
                        sexo_pi = st.radio("Sexo", ["Masculino","Femenino"], horizontal=True, key="pi_sx")
                        h_in = (imc_tall - 152.4) / 2.54
                        pi = (50 if sexo_pi == "Masculino" else 45.5) + 2.3 * h_in
                        st.info(f"**Peso ideal Devine:** {pi:.1f} kg  |  Diferencia: {imc_peso-pi:+.1f} kg")

        with c1b:
            st.markdown("#### 📐 Superficie Corporal (Mosteller)")
            sc_peso = st.number_input("Peso (kg)", 1.0, 300.0, 70.0, step=0.5, key="sc_p")
            sc_tall = st.number_input("Talla (cm)", 50.0, 250.0, 170.0, step=0.5, key="sc_t")
            sc = sqrt((sc_peso * sc_tall) / 3600)
            st.markdown(f"""
            <div class="calc-result">
                <div class="calc-val">{sc:.2f}</div>
                <div class="calc-lbl">m² (Mosteller)</div>
                <div class="calc-cat">Normal adulto: 1.7 – 1.9 m²</div>
            </div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📊 IMC pediátrico — Edad")
            imc_p_val = st.number_input("IMC del niño", 5.0, 50.0, 18.0, step=0.1, key="imc_ped")
            imc_p_age = st.number_input("Edad (años)", 2, 19, 10, step=1, key="imc_age")
            # Percentil simplificado (referencia OMS aproximada)
            if imc_p_age <= 10:
                p50 = 15 + imc_p_age * 0.3
            else:
                p50 = 17 + (imc_p_age - 10) * 0.4
            diff = imc_p_val - p50
            if diff < -2:   cat_ped = "🔵 Bajo peso"
            elif diff < 1:  cat_ped = "🟢 Normal"
            elif diff < 3:  cat_ped = "🟡 Sobrepeso"
            else:           cat_ped = "🔴 Obesidad"
            st.markdown(f'<div class="success-box"><b>Interpretación aprox.:</b> {cat_ped} (P50 referencial: {p50:.1f})</div>', unsafe_allow_html=True)

    with cal2:
        c2a, c2b = st.columns(2)
        with c2a:
            st.markdown("#### 🔬 Clearance de Creatinina (Cockcroft-Gault)")
            cg_edad = st.number_input("Edad (años)", 1, 120, 50, key="cg_e")
            cg_peso = st.number_input("Peso (kg)", 1.0, 300.0, 70.0, step=0.5, key="cg_p")
            cg_cr   = st.number_input("Creatinina sérica (mg/dL)", 0.1, 20.0, 1.0, step=0.1, key="cg_c")
            cg_sexo = st.radio("Sexo", ["Masculino","Femenino"], horizontal=True, key="cg_s")
            factor  = 1.0 if cg_sexo == "Masculino" else 0.85
            clcr = ((140 - cg_edad) * cg_peso / (72 * cg_cr)) * factor
            if clcr >= 90:       estadio, colcl = "Función normal", "#10b981"
            elif clcr >= 60:     estadio, colcl = "ERC Estadio 2", "#84cc16"
            elif clcr >= 30:     estadio, colcl = "ERC Estadio 3", "#f59e0b"
            elif clcr >= 15:     estadio, colcl = "ERC Estadio 4", "#ef4444"
            else:                estadio, colcl = "ERC Estadio 5 — Falla renal", "#991b1b"
            st.markdown(f"""
            <div class="calc-result" style="background:linear-gradient(135deg,{colcl},{colcl}cc)">
                <div class="calc-val">{clcr:.1f}</div>
                <div class="calc-lbl">mL/min</div>
                <div class="calc-cat">{estadio}</div>
            </div>""", unsafe_allow_html=True)

        with c2b:
            st.markdown("#### 🩸 Riesgo Cardiovascular simplificado")
            rv_edad   = st.number_input("Edad", 20, 80, 50, key="rv_e")
            rv_sexo   = st.radio("Sexo", ["Masculino","Femenino"], horizontal=True, key="rv_s")
            rv_fuma   = st.checkbox("Fumador activo", key="rv_f")
            rv_dm     = st.checkbox("Diabetes mellitus", key="rv_d")
            rv_hta    = st.checkbox("Hipertensión arterial", key="rv_h")
            rv_colest = st.checkbox("Colesterol > 200 mg/dL", key="rv_c")

            score = 0
            if rv_edad >= 55: score += 1
            if rv_edad >= 65: score += 1
            if rv_sexo == "Masculino": score += 1
            if rv_fuma:   score += 2
            if rv_dm:     score += 2
            if rv_hta:    score += 1
            if rv_colest: score += 1

            if score <= 1:   riesgo, rcol = "Bajo", "#10b981"
            elif score <= 3: riesgo, rcol = "Moderado", "#f59e0b"
            elif score <= 5: riesgo, rcol = "Alto", "#ef4444"
            else:            riesgo, rcol = "Muy Alto", "#991b1b"
            st.markdown(f"""
            <div class="calc-result" style="background:linear-gradient(135deg,{rcol},{rcol}cc)">
                <div class="calc-val">{score}/8</div>
                <div class="calc-lbl">Score de riesgo</div>
                <div class="calc-cat">Riesgo {riesgo}</div>
            </div>""", unsafe_allow_html=True)
            st.caption("⚠️ Esta calculadora es orientativa. Úsala como complemento de la evaluación clínica.")

    with cal3:
        c3a, c3b = st.columns(2)
        with c3a:
            st.markdown("#### 👶 Dosis pediátrica por peso")
            ped_peso = st.number_input("Peso del niño (kg)", 0.5, 100.0, 10.0, step=0.5, key="ped_p")
            ped_med  = st.selectbox("Medicamento", [
                "Paracetamol (10-15 mg/kg/dosis)",
                "Ibuprofeno (5-10 mg/kg/dosis)",
                "Amoxicilina (25-45 mg/kg/día)",
                "Azitromicina (10 mg/kg/día por 3 días)",
                "Cetirizina (0.25 mg/kg/dosis)",
                "Salbutamol (0.15 mg/kg/dosis)",
            ], key="ped_m")
            dosis_map = {
                "Paracetamol (10-15 mg/kg/dosis)": (10, 15),
                "Ibuprofeno (5-10 mg/kg/dosis)": (5, 10),
                "Amoxicilina (25-45 mg/kg/día)": (25, 45),
                "Azitromicina (10 mg/kg/día por 3 días)": (10, 10),
                "Cetirizina (0.25 mg/kg/dosis)": (0.25, 0.25),
                "Salbutamol (0.15 mg/kg/dosis)": (0.15, 0.15),
            }
            d_min, d_max = dosis_map[ped_med]
            dose_min = ped_peso * d_min
            dose_max = ped_peso * d_max
            if dose_min == dose_max:
                dose_text = f"{dose_min:.1f} mg"
            else:
                dose_text = f"{dose_min:.1f} – {dose_max:.1f} mg"
            st.markdown(f"""
            <div class="calc-result">
                <div class="calc-val">{dose_text}</div>
                <div class="calc-lbl">{ped_med.split("(")[0].strip()}</div>
                <div class="calc-cat">Para {ped_peso} kg</div>
            </div>""", unsafe_allow_html=True)
            st.caption("⚠️ Verifica siempre la dosis máxima absoluta y ajusta según indicación clínica.")

        with c3b:
            st.markdown("#### 🤰 Fecha Probable de Parto (FPP)")
            fum = st.date_input("Fecha de última menstruación (FUM)", key="fum_d")
            if fum:
                fpp = fum + timedelta(days=280)
                semanas = (date.today() - fum).days // 7
                dias_r  = (date.today() - fum).days % 7
                trimestre = "1er" if semanas < 14 else ("2do" if semanas < 28 else "3er")
                st.markdown(f"""
                <div class="calc-result">
                    <div class="calc-val">{fpp.strftime('%d/%m/%Y')}</div>
                    <div class="calc-lbl">Fecha Probable de Parto (Regla de Naegele)</div>
                    <div class="calc-cat">{trimestre} trimestre · {semanas} semanas {dias_r} días</div>
                </div>""", unsafe_allow_html=True)
                pct = min(100, (semanas / 40) * 100)
                st.progress(int(pct), text=f"Progreso gestacional: {pct:.0f}%")

# ════════════════════════════════════════════════════════════════════════════
# TAB 8 – DIRECTORIO PERSONAL
# ════════════════════════════════════════════════════════════════════════════
if t_dir:
 with t_dir:
    st.subheader("📞 Directorio Personal")
    CATEG_ICONS = {
        "Amigo":"👥","Familiar":"👨‍👩‍👧","Colega/Médico":"👨‍⚕️",
        "Restaurante":"🍽️","Lugar":"📍","Proveedor":"🏢","Otro":"📌"
    }
    dt1, dt2, dt3 = st.tabs(["📋 Mis Contactos", "⭐ Favoritos", "➕ Agregar"])

    with dt1:
        buscar_d = st.text_input("🔍 Buscar contacto")
        cat_fil  = st.multiselect("Categoría", list(CATEG_ICONS.keys()),
                                   default=list(CATEG_ICONS.keys()))
        ph_cat = ','.join(['?']*len(cat_fil)) if cat_fil else "''"
        if buscar_d:
            contactos = rows(f"""SELECT * FROM directorio WHERE categoria IN ({ph_cat})
                AND (nombre LIKE ? OR telefono LIKE ? OR email LIKE ?)
                ORDER BY favorito DESC, nombre""",
                (*cat_fil, f'%{buscar_d}%', f'%{buscar_d}%', f'%{buscar_d}%'))
        else:
            contactos = rows(f"SELECT * FROM directorio WHERE categoria IN ({ph_cat}) ORDER BY favorito DESC, nombre",
                             tuple(cat_fil))

        if not contactos:
            st.info("No hay contactos. Agrega uno en la pestaña '➕ Agregar'.")
        else:
            for ct in contactos:
                icon = CATEG_ICONS.get(ct['categoria'], "📌")
                fav  = "⭐" if ct['favorito'] else ""
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    st.markdown(f"""
                    <div class="dash-card">
                        <div style="display:flex;gap:1rem;align-items:center">
                            <div style="font-size:2rem">{icon}</div>
                            <div>
                                <b>{ct['nombre']}</b> {fav}
                                <div style="font-size:.85rem;color:#6b7280">
                                    {ct['categoria']}
                                    {' · 📞 ' + ct['telefono'] if ct['telefono'] else ''}
                                    {' · ✉️ ' + ct['email'] if ct['email'] else ''}
                                    {' · 📍 ' + ct['direccion'] if ct['direccion'] else ''}
                                </div>
                                {('<div style="font-size:.82rem;color:#9ca3af;margin-top:.2rem">📝 ' + ct['notas'] + '</div>') if ct['notas'] else ''}
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)
                    if ct['telefono']:
                        st.markdown(f'<a class="quick-btn" href="https://wa.me/52{ct["telefono"].replace(" ","")}" target="_blank">💬 WhatsApp</a>', unsafe_allow_html=True)
                with col_b:
                    if st.button("⭐" if not ct['favorito'] else "★", key=f"fav_{ct['id']}",
                                 help="Marcar/quitar favorito"):
                        qry("UPDATE directorio SET favorito=? WHERE id=?",
                            (0 if ct['favorito'] else 1, ct['id']))
                        st.rerun()
                    if st.button("🗑️", key=f"del_dir_{ct['id']}"):
                        qry("DELETE FROM directorio WHERE id=?", (ct['id'],))
                        st.rerun()

    with dt2:
        favs = rows("SELECT * FROM directorio WHERE favorito=1 ORDER BY nombre")
        if not favs:
            st.info("Aún no tienes favoritos. Marca ⭐ en algún contacto.")
        for ct in favs:
            icon = CATEG_ICONS.get(ct['categoria'], "📌")
            st.markdown(f"""
            <div class="dash-card green">
                <div style="display:flex;gap:.8rem;align-items:center">
                    <div style="font-size:1.8rem">{icon}</div>
                    <div>
                        <b>⭐ {ct['nombre']}</b>
                        <div style="font-size:.85rem;color:#6b7280">
                            {ct['categoria']}
                            {' · ' + ct['telefono'] if ct['telefono'] else ''}
                            {' · ' + ct['email'] if ct['email'] else ''}
                        </div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

    with dt3:
        with st.form("form_directorio"):
            da1, da2 = st.columns(2)
            with da1:
                d_nombre = st.text_input("Nombre *")
                d_tel    = st.text_input("Teléfono")
                d_email  = st.text_input("Email")
            with da2:
                d_cat    = st.selectbox("Categoría", list(CATEG_ICONS.keys()))
                d_dir    = st.text_input("Dirección / Lugar")
                d_fav    = st.checkbox("Marcar como favorito ⭐")
            d_notas = st.text_area("Notas", height=60)
            if st.form_submit_button("💾 Guardar contacto", type="primary"):
                if d_nombre:
                    qry("INSERT INTO directorio(nombre,telefono,email,categoria,direccion,notas,favorito) VALUES(?,?,?,?,?,?,?)",
                        (d_nombre, d_tel, d_email, d_cat, d_dir, d_notas, 1 if d_fav else 0))
                    st.success(f"✅ {d_nombre} agregado al directorio")
                    st.rerun()
                else:
                    st.warning("El nombre es obligatorio")

# ════════════════════════════════════════════════════════════════════════════
# TAB 9 – ESTADÍSTICAS
# ════════════════════════════════════════════════════════════════════════════
if t_stats:
 with t_stats:
    if _gate(3, "📊 Estadísticas", "Clínica"): st.stop()
    st.subheader("📊 Estadísticas del Consultorio")
    try:
        ing_mes  = rows("SELECT strftime('%Y-%m',fecha) as mes, SUM(monto) as total, COUNT(*) as n FROM cobros WHERE pagado=1 GROUP BY mes ORDER BY mes DESC LIMIT 12")
        citas_est = rows("SELECT status, COUNT(*) as n FROM citas GROUP BY status")
        pacs_mes  = rows("SELECT strftime('%Y-%m',created_at) as mes, COUNT(*) as n FROM pacientes GROUP BY mes ORDER BY mes DESC LIMIT 6")
        diag_freq = rows("SELECT diagnostico, COUNT(*) as n FROM consultas WHERE diagnostico IS NOT NULL AND diagnostico!='' GROUP BY diagnostico ORDER BY n DESC LIMIT 10")
        metodos   = rows("SELECT metodo_pago, SUM(monto) as total FROM cobros WHERE pagado=1 AND metodo_pago IS NOT NULL GROUP BY metodo_pago")

        col1, col2 = st.columns(2)
        with col1:
            if ing_mes:
                df_i = pd.DataFrame(ing_mes)
                fig1 = px.bar(df_i, x='mes', y='total', title='Ingresos mensuales ($)',
                              color_discrete_sequence=['#0891b2'])
                fig1.update_layout(margin=dict(t=40,b=0,l=0,r=0))
                st.plotly_chart(fig1, use_container_width=True)
            if diag_freq:
                df_d = pd.DataFrame(diag_freq)
                fig4 = px.bar(df_d, x='n', y='diagnostico', orientation='h',
                              title='Diagnósticos más frecuentes',
                              color_discrete_sequence=['#8b5cf6'])
                fig4.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig4, use_container_width=True)

        with col2:
            if citas_est:
                df_c = pd.DataFrame(citas_est)
                fig2 = px.pie(df_c, values='n', names='status', title='Citas por estado',
                              color_discrete_map={'CONFIRMADA':'#10b981','PENDIENTE':'#f59e0b','CANCELADA':'#ef4444'})
                st.plotly_chart(fig2, use_container_width=True)
            if metodos:
                df_m = pd.DataFrame(metodos)
                fig5 = px.pie(df_m, values='total', names='metodo_pago',
                              title='Ingresos por forma de pago',
                              color_discrete_sequence=px.colors.sequential.Teal)
                st.plotly_chart(fig5, use_container_width=True)

        if pacs_mes:
            df_pm = pd.DataFrame(pacs_mes)
            fig3  = px.line(df_pm, x='mes', y='n', title='Nuevos pacientes por mes',
                            markers=True, color_discrete_sequence=['#10b981'])
            fig3.update_layout(margin=dict(t=40,b=0,l=0,r=0))
            st.plotly_chart(fig3, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📋 Resumen ejecutivo")
        total_p   = one("SELECT COUNT(*) as n FROM pacientes")['n']
        total_c   = one("SELECT COUNT(*) as n FROM citas")['n']
        total_con = one("SELECT COUNT(*) as n FROM consultas")['n']
        ing_total = one("SELECT COALESCE(SUM(monto),0) as s FROM cobros WHERE pagado=1")['s']
        pend_tot  = one("SELECT COALESCE(SUM(monto),0) as s FROM cobros WHERE pagado=0")['s']
        res_data  = {
            "Métrica": ["Total pacientes","Total citas","Total consultas","Ingresos totales","Por cobrar"],
            "Valor":   [str(total_p), str(total_c), str(total_con), f"${ing_total:,.2f}", f"${pend_tot:,.2f}"]
        }
        st.dataframe(pd.DataFrame(res_data), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error cargando estadísticas: {e}")

# ════════════════════════════════════════════════════════════════════════════
# TAB 10 – RECURSOS WEB + NOTAS RÁPIDAS
# ════════════════════════════════════════════════════════════════════════════
if t_webs:
 with t_webs:
    w1, w2 = st.tabs(["🌐 Recursos Médicos", "📝 Notas Rápidas"])

    with w1:
        st.subheader("🌐 Recursos para Médicos")
        WEBS = [
            {"nombre":"CIE-10","url":"https://cie10.com.mx/","desc":"Clasificación Internacional de Enfermedades. Busca códigos de diagnóstico.","emoji":"📋","cat":"Clínica"},
            {"nombre":"Vademécum","url":"https://www.vademecum.es/","desc":"Base de datos de medicamentos, dosis, interacciones y contraindicaciones.","emoji":"💊","cat":"Clínica"},
            {"nombre":"Medscape","url":"https://www.medscape.com/","desc":"Noticias médicas, guías clínicas, calculadoras de dosis y referencias.","emoji":"🔬","cat":"Clínica"},
            {"nombre":"IMSS Medicamentos","url":"https://www.imss.gob.mx/salud-en-linea/catalogo-medicamentos","desc":"Catálogo oficial IMSS de medicamentos para prescripciones.","emoji":"🏛️","cat":"Clínica"},
            {"nombre":"COFEPRIS","url":"https://www.gob.mx/cofepris","desc":"Comisión Federal para Protección contra Riesgos Sanitarios.","emoji":"⚕️","cat":"Regulatorio"},
            {"nombre":"SAT — Portal Fiscal","url":"https://www.sat.gob.mx/","desc":"Facturación electrónica, declaraciones y trámites fiscales.","emoji":"🧾","cat":"Fiscal"},
            {"nombre":"PubMed","url":"https://pubmed.ncbi.nlm.nih.gov/","desc":"Base de datos de literatura científica y artículos biomédicos.","emoji":"📚","cat":"Investigación"},
            {"nombre":"UpToDate (acceso libre)","url":"https://www.uptodate.com/","desc":"Evidencia clínica actualizada y recomendaciones de práctica.","emoji":"🩺","cat":"Clínica"},
            {"nombre":"DoctorAhorro","url":"https://www.doctorahorro.mx/","desc":"Directorio de médicos y precios de consultas en México.","emoji":"🏥","cat":"Servicios"},
            {"nombre":"IMSS en línea","url":"https://serviciosdigitales.imss.gob.mx/","desc":"Trámites y servicios digitales del IMSS para médicos y pacientes.","emoji":"🏛️","cat":"Servicios"},
            {"nombre":"Aventura con Tablas","url":"https://aventura-tablas-pro.streamlit.app/","desc":"App educativa para niños: practica tablas de multiplicar.","emoji":"✏️","cat":"Personal"},
            {"nombre":"ContaxPert Pro","url":"https://contaxpert-app.streamlit.app/","desc":"Herramienta contable: XML/CFDI, ISR, DIOT y más.","emoji":"📊","cat":"Personal"},
        ]

        if "webs_custom_med" not in st.session_state:
            st.session_state.webs_custom_med = []
        todas = WEBS + st.session_state.webs_custom_med

        # Filtro por categoría
        cats = sorted(set(w.get('cat','General') for w in todas))
        cat_sel = st.multiselect("Filtrar por categoría", cats, default=cats)
        filtradas = [w for w in todas if w.get('cat','General') in cat_sel]

        cols = st.columns(3)
        for i, w in enumerate(filtradas):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="web-card" style="margin-bottom:14px">
                    <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.6rem">
                        <span style="font-size:1.8rem">{w['emoji']}</span>
                        <span style="font-weight:700">{w['nombre']}</span>
                    </div>
                    <div style="font-size:.82rem;opacity:.85;margin-bottom:.8rem">{w['desc']}</div>
                    <a href="{w['url']}" target="_blank"
                       style="background:rgba(255,255,255,.2);color:white;padding:6px 14px;
                       border-radius:20px;text-decoration:none;font-size:.82rem;font-weight:600;">
                       🔗 Visitar
                    </a>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### ➕ Agregar sitio personalizado")
        with st.form("form_web_med"):
            wc1, wc2 = st.columns(2)
            with wc1:
                w_nom  = st.text_input("Nombre del sitio")
                w_url  = st.text_input("URL (https://...)")
            with wc2:
                w_emo  = st.text_input("Emoji", value="🌐")
                w_cat  = st.selectbox("Categoría", ["Clínica","Regulatorio","Fiscal","Investigación","Servicios","Personal","Otro"])
                w_desc = st.text_area("Descripción", height=60)
            if st.form_submit_button("Agregar", type="primary"):
                if w_nom and w_url:
                    st.session_state.webs_custom_med.append(
                        {"nombre":w_nom,"url":w_url,"desc":w_desc,"emoji":w_emo,"cat":w_cat})
                    st.success(f"'{w_nom}' agregada.")
                    st.rerun()
                else:
                    st.warning("Nombre y URL son obligatorios.")

    with w2:
        st.subheader("📝 Notas Rápidas")
        COLOR_MAP = {"amarilla":"nota-amarilla","azul":"nota-azul","verde":"nota-verde","roja":"nota-roja"}

        nc1, nc2 = st.columns([3, 1])
        with nc1:
            notas_db = rows("SELECT * FROM notas_rapidas ORDER BY fijada DESC, created_at DESC")
        with nc2:
            if st.button("➕ Nueva Nota", type="primary", use_container_width=True):
                st.session_state['show_nota_form'] = True

        if st.session_state.get('show_nota_form'):
            with st.form("form_nota"):
                n_titulo  = st.text_input("Título de la nota")
                n_cont    = st.text_area("Contenido", height=100)
                nc_a, nc_b = st.columns(2)
                with nc_a:
                    n_color = st.selectbox("Color", ["amarilla","azul","verde","roja"])
                with nc_b:
                    n_fija  = st.checkbox("📌 Fijar nota")
                sf1, sf2 = st.columns(2)
                with sf1:
                    if st.form_submit_button("💾 Guardar", type="primary"):
                        if n_titulo or n_cont:
                            qry("INSERT INTO notas_rapidas(titulo,contenido,color,fijada) VALUES(?,?,?,?)",
                                (n_titulo, n_cont, n_color, 1 if n_fija else 0))
                            st.session_state['show_nota_form'] = False
                            st.rerun()
                with sf2:
                    if st.form_submit_button("Cancelar"):
                        st.session_state['show_nota_form'] = False; st.rerun()

        if not notas_db:
            st.markdown('<div class="info-box">Sin notas. Crea una con el botón de arriba.</div>', unsafe_allow_html=True)
        else:
            nota_cols = st.columns(3)
            for i, nota in enumerate(notas_db):
                css_class = COLOR_MAP.get(nota['color'], 'nota-amarilla')
                with nota_cols[i % 3]:
                    pin = "📌 " if nota['fijada'] else ""
                    st.markdown(f"""
                    <div class="{css_class} nota-card">
                        <div style="font-weight:700;margin-bottom:.4rem">{pin}{nota['titulo'] or '(sin título)'}</div>
                        <div style="font-size:.88rem;white-space:pre-wrap">{nota['contenido'] or ''}</div>
                        <div style="font-size:.72rem;opacity:.6;margin-top:.5rem">{nota['created_at'][:16]}</div>
                    </div>""", unsafe_allow_html=True)
                    dc1, dc2 = st.columns(2)
                    with dc1:
                        pin_label = "📌 Fijar" if not nota['fijada'] else "📌 Quitar"
                        if st.button(pin_label, key=f"pin_nota_{nota['id']}", use_container_width=True):
                            qry("UPDATE notas_rapidas SET fijada=? WHERE id=?",
                                (0 if nota['fijada'] else 1, nota['id']))
                            st.rerun()
                    with dc2:
                        if st.button("🗑️ Borrar", key=f"del_nota_{nota['id']}", use_container_width=True):
                            qry("DELETE FROM notas_rapidas WHERE id=?", (nota['id'],))
                            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# CAMBIO DE CONTRASEÑA – DOCTORES
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.get("rol") == "doctor" and st.session_state.get("user_id"):
    with st.sidebar:
        with st.expander("🔑 Cambiar contraseña"):
            _cp_act = st.text_input("Contraseña actual", type="password", key="cp_act")
            _cp_new = st.text_input("Nueva contraseña",  type="password", key="cp_new")
            _cp_rep = st.text_input("Repetir nueva",     type="password", key="cp_rep")
            if st.button("Guardar", use_container_width=True, key="cp_btn"):
                import bcrypt as _bcrypt
                _uid = st.session_state.user_id
                _row = one("SELECT password FROM usuarios WHERE id=?", (_uid,))
                if not _row or not _bcrypt.checkpw(_cp_act.encode(), _row["password"].encode()):
                    st.error("Contraseña actual incorrecta.")
                elif len(_cp_new) < 6:
                    st.error("Mínimo 6 caracteres.")
                elif _cp_new != _cp_rep:
                    st.error("Las contraseñas no coinciden.")
                else:
                    _h = _bcrypt.hashpw(_cp_new.encode(), _bcrypt.gensalt()).decode()
                    qry("UPDATE usuarios SET password=? WHERE id=?", (_h, _uid))
                    st.success("✅ Contraseña actualizada.")

# ════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════
# TAB MI SECRETARIA – solo rol doctor
# ════════════════════════════════════════════════════════════════════════════
if t_sec:
    with t_sec:
        st.subheader("🧑‍💼 Mi Secretaria")
        _doc_uid = st.session_state.get("user_id")
        _sec_row = db.execute(
            "SELECT s.id, u.nombre, u.email, u.usuario, u.activo FROM secretarias s "
            "JOIN usuarios u ON u.id=s.user_id WHERE s.doctor_id=? LIMIT 1", (_doc_uid,)
        ).fetchone()

        if _sec_row:
            st.success(f"✅ Secretaria actual: **{_sec_row['nombre']}** ({_sec_row['usuario']})")
            _s_act = bool(_sec_row["activo"])
            if st.checkbox("Cuenta activa", value=_s_act, key="sec_activa"):
                if not _s_act:
                    qry("UPDATE usuarios SET activo=1 WHERE usuario=?", (_sec_row["usuario"],))
                    st.rerun()
            else:
                if _s_act:
                    qry("UPDATE usuarios SET activo=0 WHERE usuario=?", (_sec_row["usuario"],))
                    st.rerun()
            if st.button("🗑️ Desvincular secretaria", type="secondary"):
                qry("DELETE FROM secretarias WHERE doctor_id=?", (_doc_uid,))
                st.warning("Secretaria desvinculada (usuario sigue en BD).")
                st.rerun()
        else:
            st.info("No tienes secretaria asignada. Crea una cuenta aquí:")
            with st.form("form_sec_nueva"):
                _s_nom = st.text_input("Nombre completo")
                _s_usr = st.text_input("Usuario (login)")
                _s_email = st.text_input("Email")
                _s_pw = st.text_input("Contraseña (vacío = auto)", placeholder="Dejar vacío = auto")
                if st.form_submit_button("➕ Crear secretaria"):
                    import bcrypt as _bcrypt
                    _s_pw_raw = _s_pw.strip() or _gen_pass()
                    _s_hash = _bcrypt.hashpw(_s_pw_raw.encode(), _bcrypt.gensalt()).decode()
                    try:
                        qry("INSERT INTO usuarios(nombre,email,usuario,password,plan,rol,activo) VALUES(?,?,?,?,'Básico','secretaria',1)",
                            (_s_nom, _s_email, _s_usr, _s_hash))
                        _new_uid = db.execute("SELECT id FROM usuarios WHERE usuario=?", (_s_usr,)).fetchone()["id"]
                        qry("INSERT INTO secretarias(user_id,doctor_id) VALUES(?,?)", (_new_uid, _doc_uid))
                        _enviar_credenciales(_s_email, _s_usr, _s_pw_raw)
                        st.success(f"✅ Secretaria creada. Credenciales enviadas a {_s_email}")
                        st.rerun()
                    except Exception as _ex:
                        st.error(f"Error: {_ex}")

# TAB ADMIN – GESTIÓN DE USUARIOS Y PLANES
# ════════════════════════════════════════════════════════════════════════════
if t_admin:
    with t_admin:
        st.subheader("👑 Panel de Administración")
        au1, au2, au3, au4 = st.tabs(["👤 Usuarios", "📋 Planes", "🧑‍💼 Secretarias", "📨 Prospectos"])

        with au1:
            _usuarios = rows("SELECT id,nombre,email,usuario,plan,rol,activo,licencia,created_at FROM usuarios ORDER BY created_at DESC")
            if not _usuarios:
                st.info("No hay usuarios registrados aún.")
            else:
                _df = pd.DataFrame([dict(u) for u in _usuarios])
                _edited = st.data_editor(
                    _df,
                    column_config={
                        "id":         st.column_config.NumberColumn("ID", disabled=True),
                        "nombre":     st.column_config.TextColumn("Nombre"),
                        "email":      st.column_config.TextColumn("Email", disabled=True),
                        "usuario":    st.column_config.TextColumn("Usuario"),
                        "plan":       st.column_config.SelectboxColumn("Plan", options=["Básico","Profesional","Clínica"]),
                        "rol":        st.column_config.SelectboxColumn("Rol", options=["doctor","secretaria","admin"]),
                        "activo":     st.column_config.CheckboxColumn("Activo"),
                        "licencia":   st.column_config.TextColumn("Licencia", disabled=True),
                        "created_at": st.column_config.TextColumn("Registro", disabled=True),
                    },
                    use_container_width=True, num_rows="fixed", key="editor_users"
                )
                col_g, col_e = st.columns([1, 1])
                with col_g:
                    if st.button("💾 Guardar cambios", type="primary", use_container_width=True):
                        for _, row in _edited.iterrows():
                            qry("UPDATE usuarios SET nombre=?,usuario=?,plan=?,rol=?,activo=? WHERE id=?",
                                (row["nombre"], row["usuario"], row["plan"], row["rol"], int(row["activo"]), int(row["id"])))
                            aplicar_permisos_plan(int(row["id"]), row["plan"])
                        st.success("✅ Cambios guardados.")
                        st.rerun()
                with col_e:
                    _del_id = st.number_input("ID a eliminar", min_value=1, step=1, key="del_user_id")
                    if st.button("🗑️ Eliminar usuario", type="secondary", use_container_width=True):
                        qry("DELETE FROM usuarios WHERE id=?", (_del_id,))
                        st.warning(f"Usuario {_del_id} eliminado.")
                        st.rerun()

                st.divider()
                st.markdown("**🔑 Reset de contraseña**")
                col_r1, col_r2, col_r3 = st.columns([1, 1, 1])
                with col_r1:
                    _rst_id = st.number_input("ID usuario", min_value=1, step=1, key="rst_uid")
                with col_r2:
                    _rst_pw = st.text_input("Nueva contraseña", key="rst_pw", placeholder="Dejar vacío = auto")
                with col_r3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔑 Resetear", use_container_width=True):
                        import bcrypt as _bcrypt
                        _u_row = one("SELECT email,usuario FROM usuarios WHERE id=?", (_rst_id,))
                        if _u_row:
                            _new_raw = _rst_pw.strip() or _gen_pass()
                            _new_hash = _bcrypt.hashpw(_new_raw.encode(), _bcrypt.gensalt()).decode()
                            qry("UPDATE usuarios SET password=? WHERE id=?", (_new_hash, _rst_id))
                            _enviar_credenciales(_u_row["email"], _u_row["usuario"], _new_raw)
                            st.success(f"✅ Contraseña reseteada y enviada a {_u_row['email']}")
                        else:
                            st.error("ID no encontrado.")

                st.divider()
                st.markdown("**➕ Crear Doctor**")
                with st.form("form_nuevo_doctor", clear_on_submit=True):
                    _nd_nom   = st.text_input("Nombre completo")
                    _nd_email = st.text_input("Email")
                    _nd_plan  = st.selectbox("Plan", ["Básico", "Pro"])
                    if st.form_submit_button("✅ Crear y Activar", type="primary"):
                        if _nd_nom and _nd_email:
                            import bcrypt as _bcrypt, uuid as _uuid
                            _nd_raw  = _gen_pass()
                            _nd_hash = _bcrypt.hashpw(_nd_raw.encode(), _bcrypt.gensalt()).decode()
                            _nd_usr  = f"dr{''.join(c for c in _nd_nom.lower() if c.isalpha())[:8]}{random.randint(100,999)}"
                            _nd_lic  = str(_uuid.uuid4())
                            try:
                                qry("""INSERT INTO usuarios(nombre,email,usuario,password,licencia,activo,plan,rol,created_at)
                                       VALUES(?,?,?,?,?,1,?,'doctor',(SELECT datetime('now')))""",
                                    (_nd_nom, _nd_email, _nd_usr, _nd_hash, _nd_lic, _nd_plan))
                                _nd_id = db.execute("SELECT id FROM usuarios WHERE email=?", (_nd_email,)).fetchone()
                                if _nd_id:
                                    aplicar_permisos_plan(_nd_id["id"], _nd_plan)
                                _enviar_credenciales(_nd_email, _nd_usr, _nd_raw)
                                st.success(f"✅ Doctor creado | Usuario: `{_nd_usr}` | Pass: `{_nd_raw}`")
                                st.rerun()
                            except Exception as _ex:
                                st.error(f"Error: {_ex}")
                        else:
                            st.warning("Nombre y email son obligatorios.")

        with au3:
            st.subheader("🧑‍💼 Gestión de Secretarias")
            _all_docs = rows("SELECT id, nombre FROM usuarios WHERE rol='doctor' ORDER BY nombre")
            _doc_opts = {f"{d['nombre']} (#{d['id']})": d['id'] for d in _all_docs}
            _secs = db.execute(
                "SELECT s.id, u.nombre, u.usuario, u.email, u.activo, s.doctor_id "
                "FROM secretarias s JOIN usuarios u ON u.id=s.user_id ORDER BY s.id DESC"
            ).fetchall()
            if _secs:
                _df_s = pd.DataFrame([dict(r) for r in _secs])
                _ed_s = st.data_editor(_df_s, column_config={
                    "id":        st.column_config.NumberColumn("ID", disabled=True),
                    "nombre":    st.column_config.TextColumn("Nombre"),
                    "usuario":   st.column_config.TextColumn("Usuario", disabled=True),
                    "email":     st.column_config.TextColumn("Email", disabled=True),
                    "activo":    st.column_config.CheckboxColumn("Activo"),
                    "doctor_id": st.column_config.NumberColumn("Doctor ID"),
                }, use_container_width=True, num_rows="fixed", key="ed_secs")
                col_sa, col_sb = st.columns(2)
                with col_sa:
                    if st.button("💾 Guardar", type="primary", use_container_width=True):
                        for _, _sr in _ed_s.iterrows():
                            qry("UPDATE usuarios SET nombre=?,activo=? WHERE usuario=?",
                                (_sr["nombre"], int(_sr["activo"]), _sr["usuario"]))
                            qry("UPDATE secretarias SET doctor_id=? WHERE id=?",
                                (int(_sr["doctor_id"]), int(_sr["id"])))
                        st.success("✅ Guardado."); st.rerun()
                with col_sb:
                    _del_sid = st.number_input("ID secretaria a eliminar", min_value=1, step=1, key="del_sec_id")
                    if st.button("🗑️ Eliminar", type="secondary", use_container_width=True):
                        _sec_uid = db.execute("SELECT user_id FROM secretarias WHERE id=?", (_del_sid,)).fetchone()
                        if _sec_uid:
                            qry("DELETE FROM secretarias WHERE id=?", (_del_sid,))
                            qry("DELETE FROM usuarios WHERE id=?", (_sec_uid["user_id"],))
                        st.rerun()
            else:
                st.info("Sin secretarias registradas.")
            st.divider()
            st.markdown("**➕ Crear secretaria desde admin**")
            with st.form("form_sec_admin"):
                _ac1, _ac2 = st.columns(2)
                with _ac1:
                    _as_nom = st.text_input("Nombre")
                    _as_usr = st.text_input("Usuario")
                    _as_email = st.text_input("Email")
                with _ac2:
                    _as_pw = st.text_input("Contraseña (vacío = auto)")
                    _as_doc = st.selectbox("Doctor asignado", list(_doc_opts.keys())) if _doc_opts else None
                if st.form_submit_button("Crear"):
                    import bcrypt as _bcrypt
                    _as_pw_raw = _as_pw.strip() or _gen_pass()
                    _as_hash = _bcrypt.hashpw(_as_pw_raw.encode(), _bcrypt.gensalt()).decode()
                    _as_did = _doc_opts.get(_as_doc) if _as_doc else None
                    try:
                        qry("INSERT INTO usuarios(nombre,email,usuario,password,plan,rol,activo) VALUES(?,?,?,?,'Básico','secretaria',1)",
                            (_as_nom, _as_email, _as_usr, _as_hash))
                        _as_uid = db.execute("SELECT id FROM usuarios WHERE usuario=?", (_as_usr,)).fetchone()["id"]
                        qry("INSERT INTO secretarias(user_id,doctor_id) VALUES(?,?)", (_as_uid, _as_did))
                        _enviar_credenciales(_as_email, _as_usr, _as_pw_raw)
                        st.success(f"✅ Secretaria creada → {_as_email}"); st.rerun()
                    except Exception as _ex:
                        st.error(f"Error: {_ex}")

        with au4:
            st.subheader("📨 Prospectos pendientes de pago")
            _prosp = rows("SELECT id,nombre,email,plan,activo,licencia FROM usuarios WHERE activo=0 ORDER BY id DESC")
            if not _prosp:
                st.info("No hay prospectos pendientes.")
            else:
                import bcrypt as _bcrypt, uuid as _uuid
                for _p in _prosp:
                    with st.expander(f"📧 {_p['email']} — {_p['nombre']} ({_p['plan']})"):
                        _pc1, _pc2 = st.columns(2)
                        with _pc1:
                            if st.button("✅ Activar Manual", key=f"act_{_p['id']}", type="primary", use_container_width=True):
                                _raw = _gen_pass()
                                _hsh = _bcrypt.hashpw(_raw.encode(), _bcrypt.gensalt()).decode()
                                _lic = str(_uuid.uuid4())
                                _usr = f"dr{''.join(c for c in (_p['nombre'] or _p['email']).lower() if c.isalpha())[:8]}{random.randint(100,999)}"
                                qry("""UPDATE usuarios SET activo=1,licencia=?,password=?,
                                       usuario=COALESCE(NULLIF(usuario,''),?) WHERE id=?""",
                                    (_lic, _hsh, _usr, _p['id']))
                                aplicar_permisos_plan(_p['id'], _p['plan'] or 'Básico')
                                _u = one("SELECT email,usuario FROM usuarios WHERE id=?", (_p['id'],))
                                _enviar_credenciales(_u['email'], _u['usuario'], _raw)
                                st.success(f"✅ Activado → {_u['email']}"); st.rerun()
                        with _pc2:
                            if st.button("🗑️ Eliminar", key=f"del_p_{_p['id']}", type="secondary", use_container_width=True):
                                qry("DELETE FROM usuarios WHERE id=?", (_p['id'],))
                                st.warning("Eliminado."); st.rerun()

        with au2:
            st.markdown("""
| Plan | Precio | Características |
|------|--------|----------------|
| **Básico** | $299/mes | Agenda, Pacientes, Consultas |
| **Profesional** | $599/mes | Todo Básico + Cobros, Inventario, Recetas |
| **Clínica** | $999/mes | Todo + Admin, Estadísticas, Multi-usuario |
""")
            st.info("Los cambios de plan en la pestaña Usuarios se aplican de inmediato.")
