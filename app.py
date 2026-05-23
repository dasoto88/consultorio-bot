import streamlit as st
import sqlite3
import os
import threading
import time
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch

st.set_page_config(page_title="MedPanel Pro", layout="wide", page_icon="🏥",
                   initial_sidebar_state="expanded")

# ─── KEEP-ALIVE ──────────────────────────────────────────────
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

# ─── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.med-banner {
    background: linear-gradient(135deg,#0d4f6c,#0e7490,#0891b2);
    border-radius:16px;padding:1.6rem 2rem;margin-bottom:1.5rem;
    color:white;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,.25);
}
.med-banner h1{font-size:1.9rem;font-weight:700;margin:0}
.med-banner p{font-size:.9rem;opacity:.85;margin:.3rem 0 0}
.kpi-teal{background:linear-gradient(135deg,#0891b2,#0e7490);color:white;border-radius:12px;padding:1.1rem;text-align:center;box-shadow:0 4px 14px rgba(8,145,178,.35);}
.kpi-green{background:linear-gradient(135deg,#10b981,#059669);color:white;border-radius:12px;padding:1.1rem;text-align:center;box-shadow:0 4px 14px rgba(16,185,129,.3);}
.kpi-amber{background:linear-gradient(135deg,#f59e0b,#d97706);color:white;border-radius:12px;padding:1.1rem;text-align:center;box-shadow:0 4px 14px rgba(245,158,11,.3);}
.kpi-red{background:linear-gradient(135deg,#ef4444,#dc2626);color:white;border-radius:12px;padding:1.1rem;text-align:center;}
.kpi-val{font-size:1.8rem;font-weight:700}
.kpi-lbl{font-size:.78rem;opacity:.88;margin-top:2px}
.card{background:white;border-radius:12px;padding:1.2rem;box-shadow:0 2px 12px rgba(0,0,0,.07);margin-bottom:.8rem;border-left:4px solid #0891b2;}
.card-warn{border-left-color:#f59e0b} .card-red{border-left-color:#ef4444} .card-green{border-left-color:#10b981}
.info-box{background:#e0f2fe;border-left:4px solid #0891b2;border-radius:0 8px 8px 0;padding:.8rem 1rem;margin:.5rem 0}
.warn-box{background:#fef3c7;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;padding:.8rem 1rem;margin:.5rem 0}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0d4f6c,#0e7490) !important}
[data-testid="stSidebar"] *{color:white !important}
</style>
""", unsafe_allow_html=True)

# ─── CONFIGURACIÓN ────────────────────────────────────────────
ADMIN_USER = "admin"
ADMIN_PASS = "admindasoto88"

def _s(key, default=""):
    try: return st.secrets.get(key, default)
    except: return default

CLINIC_NAME     = _s("CLINIC_NAME",      "Consultorio Médico")
DOCTOR_NAME     = _s("DOCTOR_NAME",      "Dr. Médico")
SPECIALTY       = _s("DOCTOR_SPECIALTY", "Medicina General")
PHONE           = _s("PHONE_NUMBER",     "")
CONSULTA_PRECIO = float(_s("CONSULTA_PRECIO", "500"))

# ─── BASE DE DATOS SQLite ─────────────────────────────────────
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
    """)
    conn.commit()
    return conn

db = init_db()

def qry(sql, params=()):
    cur = db.execute(sql, params)
    db.commit()
    return cur

def rows(sql, params=()):
    return [dict(r) for r in db.execute(sql, params).fetchall()]

def one(sql, params=()):
    r = db.execute(sql, params).fetchone()
    return dict(r) if r else None

# ─── RECETA PDF ───────────────────────────────────────────────
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
        "<font size='7' color='grey'>Generado con MedPanel Pro - Solo valido con sello y firma</font>",
        sty['Normal']))
    doc.build(el)
    buf.seek(0)
    return buf

# ─── SESSION ──────────────────────────────────────────────────
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# ─── LOGIN ────────────────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown(f"""<div class="med-banner">
        <div style="font-size:3rem">🏥</div>
        <h1>MedPanel Pro</h1>
        <p>{CLINIC_NAME} · Sistema de Gestion Medica</p>
    </div>""", unsafe_allow_html=True)
    _, col, _ = st.columns([1,2,1])
    with col:
        st.subheader("Acceso al Panel")
        user = st.text_input("Usuario", placeholder="admin")
        pwd  = st.text_input("Contrasena", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            u_ok = user == ADMIN_USER
            p_ok = pwd  == ADMIN_PASS
            if u_ok and p_ok:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Usuario o contrasena incorrectos")
    st.stop()

# ─── PANEL PRINCIPAL ──────────────────────────────────────────
# Sidebar
with st.sidebar:
    st.markdown(f"### 🏥 {CLINIC_NAME}")
    st.caption(f"👨‍⚕️ {DOCTOR_NAME}")
    st.caption(f"🩺 {SPECIALTY}")
    if PHONE: st.caption(f"📞 {PHONE}")
    st.markdown("---")
    st.caption(f"📅 {date.today().strftime('%d/%m/%Y')}")
    st.markdown("---")
    if st.button("🚪 Cerrar Sesion", use_container_width=True):
        st.session_state.clear(); st.rerun()

# Header
st.markdown(f"""<div class="med-banner">
    <h1>🏥 {CLINIC_NAME}</h1>
    <p>{DOCTOR_NAME} · {SPECIALTY}</p>
</div>""", unsafe_allow_html=True)

# KPIs rápidos
try:
    hoy_str = date.today().isoformat()
    citas_hoy     = rows("SELECT * FROM citas WHERE fecha LIKE ?", (f"{hoy_str}%",))
    pendientes    = rows("SELECT * FROM citas WHERE status='PENDIENTE'")
    confirmadas   = rows("SELECT * FROM citas WHERE status='CONFIRMADA'")
    total_pacs    = one("SELECT COUNT(*) as n FROM pacientes")['n']
    mes_actual    = datetime.now().strftime('%Y-%m')
    ingresos_mes  = one("SELECT COALESCE(SUM(monto),0) as s FROM cobros WHERE pagado=1 AND fecha LIKE ?",
                        (f"{mes_actual}%",))['s']
    por_cobrar    = one("SELECT COALESCE(SUM(monto),0) as s FROM cobros WHERE pagado=0")['s']
except Exception as e:
    citas_hoy = []; pendientes = []; confirmadas = []
    total_pacs = 0; ingresos_mes = 0; por_cobrar = 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.markdown(f'<div class="kpi-teal"><div class="kpi-val">{len(citas_hoy)}</div><div class="kpi-lbl">Citas hoy</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-amber"><div class="kpi-val">{len(pendientes)}</div><div class="kpi-lbl">Pendientes</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-green"><div class="kpi-val">{len(confirmadas)}</div><div class="kpi-lbl">Confirmadas</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi-teal"><div class="kpi-val">{total_pacs}</div><div class="kpi-lbl">Pacientes</div></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="kpi-green"><div class="kpi-val">${ingresos_mes:,.0f}</div><div class="kpi-lbl">Ingresos mes</div></div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─── TABS ─────────────────────────────────────────────────────
tabs = st.tabs(["📅 Agenda","👥 Pacientes","🩺 Consultas",
                "💊 Recetas","💰 Cobros","📦 Inventario",
                "📊 Estadisticas","🌐 Webs Sugeridas"])
t_agenda, t_pacs, t_cons, t_rec, t_cobros, t_inv, t_stats, t_webs = tabs

# ════════════════════════════════════════════════════════════════
# TAB 1 – AGENDA
# ════════════════════════════════════════════════════════════════
with t_agenda:
    st.subheader("📅 Agenda de Citas")

    pacientes_lista = rows("SELECT id, nombre FROM pacientes ORDER BY nombre")
    pac_opts = {f"{p['nombre']} (#{p['id']})": p['id'] for p in pacientes_lista}

    col_fil, col_nueva = st.columns([2,1])
    with col_fil:
        filtro = st.multiselect("Estado", ["PENDIENTE","CONFIRMADA","CANCELADA"],
                                default=["PENDIENTE","CONFIRMADA"])
    with col_nueva:
        st.markdown("<br>", unsafe_allow_html=True)
        nueva_cita = st.button("➕ Nueva Cita", type="primary", use_container_width=True)

    if nueva_cita:
        st.session_state['show_form_cita'] = True

    if st.session_state.get('show_form_cita'):
        with st.form("form_nueva_cita"):
            st.markdown("#### Registrar nueva cita")
            a1, a2 = st.columns(2)
            with a1:
                pac_sel = st.selectbox("Paciente *", ["— Selecciona —"] + list(pac_opts.keys()))
                motivo  = st.text_input("Motivo", value="Consulta general")
            with a2:
                fecha_c = st.date_input("Fecha")
                hora_c  = st.time_input("Hora")
                status_c = st.selectbox("Estado", ["PENDIENTE","CONFIRMADA","CANCELADA"])
            notas_c = st.text_area("Notas", height=60)
            s1, s2 = st.columns(2)
            with s1:
                if st.form_submit_button("💾 Guardar", type="primary"):
                    if pac_sel != "— Selecciona —":
                        pid = pac_opts[pac_sel]
                        fdt = f"{fecha_c}T{hora_c.strftime('%H:%M')}"
                        qry("INSERT INTO citas(paciente_id,fecha,motivo,status,notas) VALUES(?,?,?,?,?)",
                            (pid, fdt, motivo, status_c, notas_c))
                        st.success("✅ Cita registrada")
                        st.session_state['show_form_cita'] = False
                        st.rerun()
                    else:
                        st.warning("Selecciona un paciente")
            with s2:
                if st.form_submit_button("Cancelar"):
                    st.session_state['show_form_cita'] = False
                    st.rerun()

    # Listar citas
    ph = ','.join(['?']*len(filtro)) if filtro else "''"
    citas = rows(f"""
        SELECT c.id, p.nombre as paciente, c.fecha, c.motivo, c.status, c.notas
        FROM citas c JOIN pacientes p ON c.paciente_id=p.id
        WHERE c.status IN ({ph}) ORDER BY c.fecha DESC LIMIT 100
    """, tuple(filtro))

    if not citas:
        st.info("No hay citas con esos filtros.")
    else:
        for cita in citas:
            col_icon = {"CONFIRMADA":"🟢","PENDIENTE":"🟡","CANCELADA":"🔴"}.get(cita['status'],'⚪')
            with st.expander(f"{col_icon} **{cita['paciente']}** · {cita['fecha'][:16]} · {cita['motivo']}"):
                ec1, ec2, ec3 = st.columns(3)
                ec1.write(f"**Estado:** {cita['status']}")
                ec2.write(f"**Fecha:** {cita['fecha'][:16]}")
                if cita['notas']: ec3.write(f"**Notas:** {cita['notas']}")
                bc1, bc2, bc3 = st.columns(3)
                for nuevo_st in ["CONFIRMADA","CANCELADA","PENDIENTE"]:
                    with [bc1,bc2,bc3][["CONFIRMADA","CANCELADA","PENDIENTE"].index(nuevo_st)]:
                        if st.button(f"→ {nuevo_st}", key=f"st_{cita['id']}_{nuevo_st}"):
                            qry("UPDATE citas SET status=? WHERE id=?", (nuevo_st, cita['id']))
                            st.rerun()

# ════════════════════════════════════════════════════════════════
# TAB 2 – PACIENTES
# ════════════════════════════════════════════════════════════════
with t_pacs:
    st.subheader("👥 Expediente de Pacientes")

    pt1, pt2 = st.tabs(["📋 Lista de Pacientes","➕ Agregar / Editar"])

    with pt1:
        buscar_p = st.text_input("🔍 Buscar paciente (nombre, tel, RFC)")
        if buscar_p:
            pacs = rows("SELECT * FROM pacientes WHERE nombre LIKE ? OR telefono LIKE ? OR email LIKE ? ORDER BY nombre",
                       (f'%{buscar_p}%',f'%{buscar_p}%',f'%{buscar_p}%'))
        else:
            pacs = rows("SELECT * FROM pacientes ORDER BY nombre LIMIT 100")
        st.metric("Pacientes encontrados", len(pacs))
        for pac in pacs:
            with st.expander(f"**{pac['nombre']}** · {pac['telefono'] or '—'} · {pac.get('tipo_sangre') or ''}"):
                p1, p2, p3 = st.columns(3)
                p1.write(f"**Email:** {pac['email'] or '—'}")
                p1.write(f"**Nac:** {pac['fecha_nac'] or '—'}")
                p1.write(f"**Sexo:** {pac['sexo'] or '—'}")
                p2.write(f"**Sangre:** {pac['tipo_sangre'] or '—'}")
                p2.write(f"**Alergias:** {pac['alergias'] or '—'}")
                p3.write(f"**Antecedentes:** {pac['antecedentes'] or '—'}")
                if pac['notas']:
                    st.markdown(f'<div class="info-box">📝 {pac["notas"]}</div>', unsafe_allow_html=True)
                hist_cons = rows("SELECT * FROM consultas WHERE paciente_id=? ORDER BY fecha DESC LIMIT 5",
                                 (pac['id'],))
                if hist_cons:
                    st.markdown("**Ultimas consultas:**")
                    for hc in hist_cons:
                        st.caption(f"• {hc['fecha'][:10]} — {hc['diagnostico'] or hc['motivo']}")
                if st.button("🗑️ Eliminar", key=f"del_pac_{pac['id']}"):
                    qry("DELETE FROM pacientes WHERE id=?", (pac['id'],))
                    st.rerun()

    with pt2:
        with st.form("form_paciente"):
            st.markdown("**Datos del paciente**")
            fp1, fp2, fp3 = st.columns(3)
            with fp1:
                p_nombre  = st.text_input("Nombre completo *")
                p_tel     = st.text_input("Telefono *")
                p_email   = st.text_input("Email")
            with fp2:
                p_nac     = st.date_input("Fecha de nacimiento", value=None)
                p_sexo    = st.selectbox("Sexo", ["No especificado","Masculino","Femenino","Otro"])
                p_sangre  = st.selectbox("Tipo de sangre", ["—","A+","A-","B+","B-","AB+","AB-","O+","O-"])
            with fp3:
                p_dir     = st.text_area("Direccion", height=68)
                p_alerg   = st.text_input("Alergias conocidas")
            p_ant   = st.text_area("Antecedentes médicos", height=60)
            p_meds  = st.text_area("Medicamentos actuales", height=60)
            p_notas = st.text_area("Notas adicionales", height=60)
            if st.form_submit_button("💾 Guardar Paciente", type="primary"):
                if p_nombre and p_tel:
                    try:
                        qry("""INSERT INTO pacientes(nombre,telefono,email,fecha_nac,sexo,
                               tipo_sangre,direccion,alergias,antecedentes,medicamentos,notas)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                            (p_nombre, p_tel, p_email,
                             str(p_nac) if p_nac else None,
                             p_sexo, p_sangre if p_sangre != "—" else None,
                             p_dir, p_alerg, p_ant, p_meds, p_notas))
                        st.success(f"✅ Paciente {p_nombre} registrado")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Nombre y teléfono son obligatorios")

# ════════════════════════════════════════════════════════════════
# TAB 3 – CONSULTAS (SOAP)
# ════════════════════════════════════════════════════════════════
with t_cons:
    st.subheader("🩺 Consultas Médicas")

    ct1, ct2 = st.tabs(["📋 Ver Consultas","➕ Nueva Consulta"])

    with ct1:
        consultas = rows("""
            SELECT c.id, p.nombre as paciente, c.fecha, c.motivo,
                   c.diagnostico, c.tratamiento, c.tension, c.peso, c.temperatura
            FROM consultas c JOIN pacientes p ON c.paciente_id=p.id
            ORDER BY c.fecha DESC LIMIT 50
        """)
        if not consultas:
            st.info("Sin consultas registradas.")
        for con in consultas:
            with st.expander(f"**{con['paciente']}** · {(con['fecha'] or '')[:10]} · {con['diagnostico'] or con['motivo']}"):
                v1,v2,v3 = st.columns(3)
                v1.write(f"**Motivo:** {con['motivo']}")
                v1.write(f"**Diagnostico:** {con['diagnostico'] or '—'}")
                v2.write(f"**Tension:** {con['tension'] or '—'}")
                v2.write(f"**Peso:** {str(con['peso']) + ' kg' if con['peso'] else '—'}")
                v3.write(f"**Temp:** {str(con['temperatura']) + ' C' if con['temperatura'] else '—'}")
                if con['tratamiento']:
                    st.write(f"**Tratamiento:** {con['tratamiento']}")

    with ct2:
        pac_todos = rows("SELECT id, nombre FROM pacientes ORDER BY nombre")
        pmap = {f"{p['nombre']} (#{p['id']})": p['id'] for p in pac_todos}
        with st.form("form_consulta"):
            st.markdown("**Nueva Consulta**")
            nc1, nc2 = st.columns(2)
            with nc1:
                pac_c = st.selectbox("Paciente *", ["— Selecciona —"] + list(pmap.keys()))
                motivo_c = st.text_input("Motivo de consulta *", value="Consulta general")
                fecha_con = st.date_input("Fecha")
            with nc2:
                tension  = st.text_input("Tension arterial (ej: 120/80)")
                peso     = st.number_input("Peso (kg)", 0.0, 300.0, step=0.5)
                talla    = st.number_input("Talla (cm)", 0.0, 250.0, step=0.5)
            nc3, nc4 = st.columns(2)
            with nc3:
                temperatura = st.number_input("Temperatura (°C)", 0.0, 45.0, step=0.1)
                glucosa     = st.number_input("Glucosa (mg/dL)", 0.0, 800.0, step=1.0)
                spo2        = st.number_input("SpO2 (%)", 0.0, 100.0, step=0.5)
            with nc4:
                sintomas    = st.text_area("Sintomas (S)", height=80)
            diagnostico = st.text_area("Diagnostico (A)", height=80)
            tratamiento = st.text_area("Tratamiento (P)", height=80)
            receta_c    = st.text_area("Receta / Medicamentos", height=80)
            obs         = st.text_area("Observaciones", height=60)

            cobrar_auto = st.checkbox("Generar cobro automaticamente", value=True)
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
                        qry("""INSERT INTO cobros(paciente_id,consulta_id,concepto,monto,fecha)
                               VALUES(?,?,?,?,?)""",
                            (pid, cons_id, "Consulta médica", monto_cons, fecha_str))
                    st.success("✅ Consulta registrada")
                    st.rerun()
                else:
                    st.warning("Selecciona paciente y motivo")

# ════════════════════════════════════════════════════════════════
# TAB 4 – RECETAS PDF
# ════════════════════════════════════════════════════════════════
with t_rec:
    st.subheader("💊 Generador de Recetas PDF")
    st.markdown('<div class="info-box">Genera recetas médicas profesionales en PDF listas para imprimir o enviar.</div>', unsafe_allow_html=True)

    pac_rec = rows("SELECT id, nombre FROM pacientes ORDER BY nombre")
    prmap = {f"{p['nombre']} (#{p['id']})": p['id'] for p in pac_rec}

    with st.form("form_receta"):
        r1, r2 = st.columns(2)
        with r1:
            pac_r   = st.selectbox("Paciente", ["— Manual —"] + list(prmap.keys()))
            pac_nom = st.text_input("O escribe nombre del paciente")
            edad_r  = st.text_input("Edad")
        with r2:
            diag_r  = st.text_area("Diagnostico", height=80)
        receta_txt = st.text_area("Medicamentos y posologia *", height=150,
                                   placeholder="Ejemplo:\nAmoxicilina 500mg - 1 capsula cada 8 hrs por 7 dias\nIbuprofeno 400mg - 1 tableta cada 12 hrs con alimentos")
        if st.form_submit_button("📄 Generar PDF", type="primary"):
            if receta_txt.strip():
                nombre_pac = pac_nom if pac_nom else (pac_r.split(" (#")[0] if pac_r != "— Manual —" else "Paciente")
                if edad_r: nombre_pac += f", {edad_r} años"
                pdf = generar_receta_pdf(nombre_pac, diag_r, receta_txt)
                st.success("✅ Receta generada")
                st.download_button("📥 Descargar Receta PDF", pdf,
                                   f"Receta_{nombre_pac.split(',')[0]}_{date.today()}.pdf",
                                   "application/pdf", use_container_width=True, type="primary")
            else:
                st.warning("Escribe los medicamentos")

    # Recetas de consultas pasadas
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
            st.write(f"**Diagnostico:** {cr['diagnostico'] or '—'}")
            st.write(f"**Receta:** {cr['receta']}")
            if st.button("📄 PDF de esta receta", key=f"pdf_cr_{cr['id']}"):
                pdf2 = generar_receta_pdf(cr['nombre'], cr['diagnostico'], cr['receta'])
                st.download_button("📥 Descargar", pdf2,
                                   f"Receta_{cr['nombre'].split()[0]}_{cr['id']}.pdf",
                                   "application/pdf", key=f"dl_cr_{cr['id']}")

# ════════════════════════════════════════════════════════════════
# TAB 5 – COBROS
# ════════════════════════════════════════════════════════════════
with t_cobros:
    st.subheader("💰 Cobros y Pagos")

    cob1, cob2 = st.columns([2,1])
    with cob1:
        filtro_cob = st.radio("Ver", ["Todos","Pendientes","Pagados"], horizontal=True)
    with cob2:
        nuevo_cobro = st.button("➕ Nuevo Cobro", type="primary")

    if nuevo_cobro:
        st.session_state['show_form_cobro'] = True

    if st.session_state.get('show_form_cobro'):
        pac_cob = rows("SELECT id, nombre FROM pacientes ORDER BY nombre")
        pcmap   = {f"{p['nombre']} (#{p['id']})": p['id'] for p in pac_cob}
        with st.form("form_cobro"):
            cc1, cc2 = st.columns(2)
            with cc1:
                pac_cb = st.selectbox("Paciente *", ["— Selecciona —"] + list(pcmap.keys()))
                concepto_cb = st.text_input("Concepto", value="Consulta médica")
            with cc2:
                monto_cb   = st.number_input("Monto ($)", value=CONSULTA_PRECIO, step=50.0)
                metodo_cb  = st.selectbox("Forma de pago", ["Efectivo","Transferencia","Tarjeta débito","Tarjeta crédito","—"])
                pagado_cb  = st.checkbox("Ya pagado", value=True)
            fecha_cb = st.date_input("Fecha")
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.form_submit_button("💾 Guardar", type="primary"):
                    if pac_cb != "— Selecciona —":
                        qry("""INSERT INTO cobros(paciente_id,concepto,monto,pagado,metodo_pago,fecha)
                               VALUES(?,?,?,?,?,?)""",
                            (pcmap[pac_cb], concepto_cb, monto_cb,
                             1 if pagado_cb else 0,
                             metodo_cb if metodo_cb != "—" else None,
                             str(fecha_cb)))
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

    mc1,mc2,mc3 = st.columns(3)
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

# ════════════════════════════════════════════════════════════════
# TAB 6 – INVENTARIO
# ════════════════════════════════════════════════════════════════
with t_inv:
    st.subheader("📦 Inventario de Medicamentos y Materiales")

    inv1, inv2 = st.tabs(["📋 Stock actual","➕ Agregar / Actualizar"])

    with inv1:
        inventario = rows("SELECT * FROM inventario ORDER BY categoria, nombre")
        bajos = [i for i in inventario if i['cantidad'] <= i['minimo']]
        if bajos:
            st.markdown(f'<div class="warn-box">⚠️ <b>{len(bajos)} artículos</b> por debajo del mínimo: {", ".join(b["nombre"] for b in bajos)}</div>', unsafe_allow_html=True)

        if not inventario:
            st.info("Inventario vacío. Agrega artículos en la pestaña siguiente.")
        else:
            df_inv = pd.DataFrame(inventario)
            df_inv['Alerta'] = df_inv.apply(lambda r: '🔴 BAJO' if r['cantidad'] <= r['minimo'] else '🟢 OK', axis=1)
            st.dataframe(df_inv[['nombre','categoria','cantidad','unidad','minimo','Alerta','proveedor','vencimiento']],
                         use_container_width=True, hide_index=True)

            st.markdown("---")
            for item in inventario:
                with st.expander(f"{'🔴' if item['cantidad']<=item['minimo'] else '🟢'} **{item['nombre']}** — {item['cantidad']} {item['unidad']}"):
                    i1,i2,i3 = st.columns(3)
                    i1.write(f"**Categoría:** {item['categoria']}")
                    i1.write(f"**Mínimo:** {item['minimo']}")
                    i2.write(f"**Precio:** ${item['precio'] or 0:,.2f}")
                    i2.write(f"**Proveedor:** {item['proveedor'] or '—'}")
                    i3.write(f"**Vencimiento:** {item['vencimiento'] or '—'}")
                    if item['notas']: st.write(f"**Notas:** {item['notas']}")
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
                inv_min  = st.number_input("Cantidad mínima", min_value=0, value=5, step=1)
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

# ════════════════════════════════════════════════════════════════
# TAB 7 – ESTADÍSTICAS
# ════════════════════════════════════════════════════════════════
with t_stats:
    st.subheader("📊 Estadísticas del Consultorio")

    try:
        # Ingresos por mes
        ing_mes = rows("""
            SELECT strftime('%Y-%m', fecha) as mes, SUM(monto) as total, COUNT(*) as n
            FROM cobros WHERE pagado=1
            GROUP BY mes ORDER BY mes DESC LIMIT 12
        """)
        # Citas por estado
        citas_est = rows("SELECT status, COUNT(*) as n FROM citas GROUP BY status")
        # Pacientes nuevos por mes
        pacs_mes = rows("""
            SELECT strftime('%Y-%m', created_at) as mes, COUNT(*) as n
            FROM pacientes GROUP BY mes ORDER BY mes DESC LIMIT 6
        """)
        # Diagnosticos frecuentes
        diag_freq = rows("""
            SELECT diagnostico, COUNT(*) as n FROM consultas
            WHERE diagnostico IS NOT NULL AND diagnostico!=''
            GROUP BY diagnostico ORDER BY n DESC LIMIT 10
        """)

        col_stat1, col_stat2 = st.columns(2)

        with col_stat1:
            if ing_mes:
                df_ing = pd.DataFrame(ing_mes)
                fig1 = px.bar(df_ing, x='mes', y='total',
                              title='Ingresos mensuales ($)',
                              color_discrete_sequence=['#0891b2'])
                fig1.update_layout(margin=dict(t=40,b=0,l=0,r=0))
                st.plotly_chart(fig1, use_container_width=True)

            if pacs_mes:
                df_pm = pd.DataFrame(pacs_mes)
                fig3 = px.line(df_pm, x='mes', y='n',
                               title='Nuevos pacientes por mes',
                               markers=True, color_discrete_sequence=['#10b981'])
                st.plotly_chart(fig3, use_container_width=True)

        with col_stat2:
            if citas_est:
                df_ce = pd.DataFrame(citas_est)
                fig2 = px.pie(df_ce, values='n', names='status',
                              title='Citas por estado',
                              color_discrete_map={'CONFIRMADA':'#10b981',
                                                  'PENDIENTE':'#f59e0b',
                                                  'CANCELADA':'#ef4444'})
                st.plotly_chart(fig2, use_container_width=True)

            if diag_freq:
                df_df = pd.DataFrame(diag_freq)
                fig4 = px.bar(df_df, x='n', y='diagnostico', orientation='h',
                              title='Diagnósticos más frecuentes',
                              color_discrete_sequence=['#6366f1'])
                fig4.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig4, use_container_width=True)

        # Resumen ejecutivo
        st.markdown("---")
        st.markdown("#### Resumen ejecutivo")
        total_p   = one("SELECT COUNT(*) as n FROM pacientes")['n']
        total_c   = one("SELECT COUNT(*) as n FROM citas")['n']
        total_con = one("SELECT COUNT(*) as n FROM consultas")['n']
        ing_total = one("SELECT COALESCE(SUM(monto),0) as s FROM cobros WHERE pagado=1")['s']
        pend_tot  = one("SELECT COALESCE(SUM(monto),0) as s FROM cobros WHERE pagado=0")['s']

        res_data = {
            "Métrica": ["Total pacientes","Total citas","Total consultas","Ingresos totales","Por cobrar"],
            "Valor":   [str(total_p), str(total_c), str(total_con),
                        f"${ing_total:,.2f}", f"${pend_tot:,.2f}"]
        }
        st.dataframe(pd.DataFrame(res_data), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error cargando estadísticas: {e}")

# ════════════════════════════════════════════════════════════════
# TAB 8 – WEBS SUGERIDAS
# ════════════════════════════════════════════════════════════════
with t_webs:
    st.subheader("🌐 Webs Sugeridas para Médicos")

    WEBS = [
        {"nombre":"MedPanel Pro","url":"https://consultorio-bot.streamlit.app/",
         "desc":"Tu sistema de gestión médica. Agendas, expedientes, recetas y estadísticas.","emoji":"🏥"},
        {"nombre":"CIE-10 en Línea","url":"https://cie10.com.mx/",
         "desc":"Clasificación Internacional de Enfermedades. Busca códigos de diagnóstico.","emoji":"📋"},
        {"nombre":"Vademécum Farmacológico","url":"https://www.vademecum.es/",
         "desc":"Base de datos de medicamentos, dosis e interacciones farmacológicas.","emoji":"💊"},
        {"nombre":"IMSS Catálogo Medicamentos","url":"https://www.imss.gob.mx/salud-en-linea/catalogo-medicamentos",
         "desc":"Catálogo oficial de medicamentos del IMSS para prescripciones y referencias.","emoji":"🏛️"},
        {"nombre":"Medscape","url":"https://www.medscape.com/",
         "desc":"Noticias médicas, guías clínicas y calculadoras de dosis.","emoji":"🔬"},
        {"nombre":"SAT — Portal Fiscal","url":"https://www.sat.gob.mx/",
         "desc":"Portal del SAT para facturas electrónicas, declaraciones y trámites.","emoji":"🧾"},
        {"nombre":"COFEPRIS","url":"https://www.gob.mx/cofepris",
         "desc":"Comisión Federal para la Protección contra Riesgos Sanitarios.","emoji":"⚕️"},
        {"nombre":"Aventura con las Tablas","url":"https://aventura-tablas-pro.streamlit.app/",
         "desc":"App educativa para niños: practica las tablas de multiplicar.","emoji":"✏️"},
        {"nombre":"ContaXpert Pro","url":"https://contaxpert-app.streamlit.app/",
         "desc":"Herramienta contable: convertir XML/CFDI, calculadora ISR, DIOT y más.","emoji":"📊"},
    ]

    if "webs_custom_med" not in st.session_state:
        st.session_state.webs_custom_med = []

    todas = WEBS + st.session_state.webs_custom_med
    cols = st.columns(3)
    for i, w in enumerate(todas):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#0d9488,#0f766e);border-radius:12px;
            padding:18px;margin-bottom:14px;color:white;">
                <div style="font-size:2rem">{w['emoji']}</div>
                <div style="font-weight:700;font-size:1rem;margin:6px 0">{w['nombre']}</div>
                <div style="font-size:.82rem;opacity:.9;margin-bottom:10px">{w['desc']}</div>
                <a href="{w['url']}" target="_blank"
                   style="background:rgba(255,255,255,.2);color:white;padding:6px 14px;
                   border-radius:20px;text-decoration:none;font-size:.82rem;font-weight:600;">
                   🔗 Visitar
                </a>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("➕ Agregar web personalizada")
    with st.form("form_web_med"):
        wc1, wc2 = st.columns(2)
        with wc1:
            w_nom  = st.text_input("Nombre del sitio")
            w_url  = st.text_input("URL (https://...)")
        with wc2:
            w_emo  = st.text_input("Emoji", value="🌐")
            w_desc = st.text_area("Descripción", height=80)
        if st.form_submit_button("Agregar", type="primary"):
            if w_nom and w_url:
                st.session_state.webs_custom_med.append(
                    {"nombre":w_nom,"url":w_url,"desc":w_desc,"emoji":w_emo})
                st.success(f"'{w_nom}' agregada.")
                st.rerun()
            else:
                st.warning("Nombre y URL son obligatorios.")
