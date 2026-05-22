import streamlit as st
import asyncio
import os
import threading
import time
import requests
import subprocess
import sys
from datetime import datetime, timedelta, date
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch

st.set_page_config(page_title="MedPanel Pro", layout="wide", page_icon="🏥",
                   initial_sidebar_state="expanded")

# ================= AUTO MIGRACIÓN DB =================
@st.cache_resource
def _migrar_db():
    # Generate prisma client first (no DATABASE_URL needed)
    try:
        subprocess.run(
            [sys.executable, "-m", "prisma", "generate"],
            capture_output=True, text=True, timeout=60
        )
    except Exception:
        pass
    # Push schema to DB (needs DATABASE_URL)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "prisma", "db", "push", "--accept-data-loss"],
            capture_output=True, text=True, timeout=60
        )
        return f"OK: {result.stdout[-200:]}" if result.returncode == 0 else f"ERR: {result.stderr[-200:]}"
    except Exception as e:
        return f"Skip: {e}"
_migrar_db()

# ================= KEEP-ALIVE =================
@st.cache_resource
def _start_keep_alive():
    def _ping():
        while True:
            time.sleep(290)
            try:
                requests.get("https://consultorio-bot-9j3t.onrender.com/", timeout=10)
            except Exception:
                pass
    t = threading.Thread(target=_ping, daemon=True)
    t.start()
    return True
_start_keep_alive()

# ================= CSS MÉDICO PROFESIONAL =================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.med-banner {
    background: linear-gradient(135deg, #0d4f6c 0%, #0e7490 50%, #0891b2 100%);
    border-radius: 16px; padding: 1.6rem 2rem; margin-bottom: 1.5rem;
    border: 1px solid rgba(8,145,178,0.4);
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
    color: white; text-align: center;
}
.med-banner h1 { font-size: 1.9rem; font-weight: 700; margin: 0; }
.med-banner p  { font-size: 0.9rem; opacity: 0.85; margin: 0.3rem 0 0; }

.kpi-teal {
    background: linear-gradient(135deg, #0891b2, #0e7490);
    color: white; border-radius: 12px; padding: 1.1rem 1rem;
    text-align: center; box-shadow: 0 4px 14px rgba(8,145,178,0.35);
}
.kpi-green {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white; border-radius: 12px; padding: 1.1rem 1rem;
    text-align: center; box-shadow: 0 4px 14px rgba(16,185,129,0.3);
}
.kpi-amber {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    color: white; border-radius: 12px; padding: 1.1rem 1rem;
    text-align: center; box-shadow: 0 4px 14px rgba(245,158,11,0.3);
}
.kpi-red {
    background: linear-gradient(135deg, #ef4444, #dc2626);
    color: white; border-radius: 12px; padding: 1.1rem 1rem;
    text-align: center; box-shadow: 0 4px 14px rgba(239,68,68,0.3);
}
.kpi-val { font-size: 1.8rem; font-weight: 700; }
.kpi-lbl { font-size: 0.78rem; opacity: 0.88; margin-top: 2px; }

.card {
    background: white; border-radius: 12px; padding: 1.2rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07); margin-bottom: 0.8rem;
    border-left: 4px solid #0891b2;
}
.card-warn  { border-left-color: #f59e0b; }
.card-red   { border-left-color: #ef4444; }
.card-green { border-left-color: #10b981; }

.info-box {
    background: #e0f2fe; border-left: 4px solid #0891b2;
    border-radius: 0 8px 8px 0; padding: 0.8rem 1rem; margin: 0.5rem 0;
}
.warn-box {
    background: #fef3c7; border-left: 4px solid #f59e0b;
    border-radius: 0 8px 8px 0; padding: 0.8rem 1rem; margin: 0.5rem 0;
}

[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d4f6c 0%, #0e7490 100%) !important; }
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stMetric { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ================= CONFIG =================
ADMIN_USER = "admin"
ADMIN_PASS = "admindasoto88"

def _secret(key, default=""):
    try:
        return st.secrets.get(key, default)
    except:
        return default

CLINIC_NAME   = _secret("CLINIC_NAME",      "Consultorio Médico")
DOCTOR_NAME   = _secret("DOCTOR_NAME",      "Dr. Médico")
SPECIALTY     = _secret("DOCTOR_SPECIALTY", "Medicina General")
PHONE         = _secret("PHONE_NUMBER",     "")
ADDRESS       = _secret("ADDRESS",          "")
LOGO_URL      = _secret("LOGO_URL",         "")
CONSULTA_PRECIO = float(_secret("CONSULTA_PRECIO", "500"))

# ================= DB =================
@st.cache_resource
def init_db():
    from prisma import Prisma
    client = Prisma()
    asyncio.run(client.connect())
    return client

def run(coro):
    return asyncio.run(coro)

db = None
DB_OK = False
DB_ERR = "Base de datos no inicializada"
try:
    db = init_db()
    DB_OK = True
    DB_ERR = ""
except Exception as e:
    DB_OK = False
    DB_ERR = str(e)

# ================= RECETA PDF =================
def generar_receta_pdf(paciente_nombre, paciente_edad, diagnostico, receta_texto, doctor, especialidad, clinica):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            topMargin=0.6*inch, bottomMargin=0.6*inch,
                            leftMargin=0.8*inch, rightMargin=0.8*inch)
    styles = getSampleStyleSheet()
    el = []

    # Header
    header_data = [[
        Paragraph(f"<b>{clinica}</b>", styles['Title']),
        Paragraph(f"<b>{doctor}</b><br/><font size='9'>{especialidad}</font>", styles['Normal'])
    ]]
    ht = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    ht.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), colors.HexColor('#0e7490')),
        ('TEXTCOLOR',  (0,0),(-1,-1), colors.white),
        ('VALIGN',     (0,0),(-1,-1), 'MIDDLE'),
        ('PADDING',    (0,0),(-1,-1), 12),
    ]))
    el.append(ht)
    el.append(Spacer(1, 0.3*inch))

    # Datos paciente
    fecha_str = datetime.now().strftime('%d/%m/%Y')
    el.append(Paragraph(f"<b>Paciente:</b> {paciente_nombre}   &nbsp;&nbsp; <b>Edad:</b> {paciente_edad}   &nbsp;&nbsp; <b>Fecha:</b> {fecha_str}", styles['Normal']))
    el.append(Spacer(1, 0.1*inch))
    el.append(Paragraph(f"<b>Diagnóstico:</b> {diagnostico or '—'}", styles['Normal']))
    el.append(Spacer(1, 0.2*inch))
    el.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0e7490')))
    el.append(Spacer(1, 0.2*inch))

    # Símbolo Rx
    el.append(Paragraph("<font size='20' color='#0e7490'><b>℞</b></font>", styles['Normal']))
    el.append(Spacer(1, 0.15*inch))

    # Receta
    for linea in receta_texto.strip().split('\n'):
        if linea.strip():
            el.append(Paragraph(f"• {linea.strip()}", styles['Normal']))
            el.append(Spacer(1, 0.05*inch))

    el.append(Spacer(1, 0.5*inch))
    el.append(HRFlowable(width="3*inch", thickness=0.5, color=colors.grey))
    el.append(Paragraph(f"Firma del médico: {doctor}", styles['Normal']))
    el.append(Spacer(1, 0.1*inch))
    el.append(Paragraph("<font size='7' color='grey'>Documento generado con MedPanel Pro • Solo válido con sello y firma del médico tratante</font>", styles['Normal']))

    doc.build(el)
    buf.seek(0)
    return buf

# ================= SESSION =================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# ==========================================
# LOGIN
# ==========================================
if not st.session_state.logged_in:
    st.markdown(f"""<div class="med-banner">
        <div style="font-size:3rem">🏥</div>
        <h1>MedPanel Pro</h1>
        <p>{CLINIC_NAME} · Sistema de Gestión Médica</p>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("Acceso al Panel")
        user = st.text_input("Usuario", placeholder="admin")
        pwd  = st.text_input("Contraseña", type="password")
        if st.button("🔐 Entrar", type="primary", use_container_width=True):
            u_ok = user == _secret("ADMIN_USER", ADMIN_USER)
            p_ok = pwd  == _secret("ADMIN_PASSWORD", ADMIN_PASS)
            if u_ok and p_ok:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    st.stop()

# ==========================================
# PANEL PRINCIPAL
# ==========================================
if not DB_OK:
    st.error(f"❌ Error conectando a la base de datos: {DB_ERR}")
    st.info("Verifica que la variable de entorno DATABASE_URL esté configurada correctamente en Render.")
    if st.button("Cerrar sesión"):
        st.session_state.clear(); st.rerun()
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown(f"### 🏥 {CLINIC_NAME}")
    st.caption(f"👨‍⚕️ {DOCTOR_NAME}")
    st.caption(f"🩺 {SPECIALTY}")
    if PHONE:
        st.caption(f"📞 {PHONE}")
    st.markdown("---")
    st.caption(f"📅 {date.today().strftime('%A %d/%m/%Y').capitalize()}")
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear(); st.rerun()

# Header
st.markdown(f"""<div class="med-banner">
    <h1>🏥 {CLINIC_NAME}</h1>
    <p>{DOCTOR_NAME} · {SPECIALTY}</p>
</div>""", unsafe_allow_html=True)

# Cargar datos para KPIs
try:
    citas_all     = run(db.cita.find_many(include={'paciente': True}))
    pacientes_all = run(db.paciente.find_many())
    cobros_all    = run(db.cobro.find_many())
    hoy_str       = datetime.now().date()
    citas_hoy     = [c for c in citas_all if c.fecha.date() == hoy_str]
    pendientes    = [c for c in citas_all if c.status == "PENDIENTE"]
    confirmadas   = [c for c in citas_all if c.status == "CONFIRMADA"]
    ingresos_mes  = sum(c.monto for c in cobros_all if c.pagado and c.fecha.month == datetime.now().month)
    pendientes_cobro = sum(c.monto for c in cobros_all if not c.pagado)
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    citas_all = []; pacientes_all = []; cobros_all = []
    citas_hoy = []; pendientes = []; confirmadas = []; ingresos_mes = 0; pendientes_cobro = 0

# KPIs
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="kpi-teal"><div class="kpi-val">{len(citas_hoy)}</div><div class="kpi-lbl">Citas hoy</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-amber"><div class="kpi-val">{len(pendientes)}</div><div class="kpi-lbl">Pendientes</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-green"><div class="kpi-val">{len(confirmadas)}</div><div class="kpi-lbl">Confirmadas</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi-teal"><div class="kpi-val">{len(pacientes_all)}</div><div class="kpi-lbl">Pacientes</div></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="kpi-green"><div class="kpi-val">${ingresos_mes:,.0f}</div><div class="kpi-lbl">Ingresos este mes</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Tabs
tab_agenda, tab_pacientes, tab_consultas, tab_recetas, tab_cobros, tab_inventario, tab_stats, tab_webs = st.tabs([
    "📅 Agenda",
    "👥 Pacientes",
    "🩺 Consultas",
    "💊 Recetas",
    "💰 Cobros",
    "📦 Inventario",
    "📊 Estadísticas",
    "🌐 Webs Sugeridas"
])

# ─────────────────────────────────────────────────
# TAB 1: AGENDA
# ─────────────────────────────────────────────────
with tab_agenda:
    st.subheader("📅 Agenda de Citas")

    col_fil, col_nueva = st.columns([2, 1])
    with col_fil:
        filtro_status = st.multiselect("Filtrar por estado",
                                        ["PENDIENTE","CONFIRMADA","CANCELADA"],
                                        default=["PENDIENTE","CONFIRMADA"])
    with col_nueva:
        st.markdown("<br>", unsafe_allow_html=True)
        agregar_manual = st.button("➕ Nueva cita manual", use_container_width=True)

    if agregar_manual:
        with st.expander("📝 Registrar nueva cita", expanded=True):
            if pacientes_all:
                pac_dict = {f"{p.nombre or p.telefono} ({p.telefono})": p.id for p in pacientes_all}
                pac_sel = st.selectbox("Paciente", list(pac_dict.keys()))
                pac_id = pac_dict[pac_sel]
            else:
                st.warning("No hay pacientes registrados aún.")
                pac_id = None

            col_fd, col_fh = st.columns(2)
            with col_fd:
                fecha_cita = st.date_input("Fecha", value=date.today())
            with col_fh:
                hora_cita = st.time_input("Hora", value=datetime.now().replace(hour=10, minute=0).time())
            motivo_cita = st.text_input("Motivo", value="Consulta general")

            if st.button("💾 Guardar cita", type="primary") and pac_id:
                fecha_dt = datetime.combine(fecha_cita, hora_cita)
                run(db.cita.create(data={
                    'pacienteId': pac_id,
                    'fecha': fecha_dt,
                    'motivo': motivo_cita,
                    'status': 'PENDIENTE'
                }))
                st.success("✅ Cita registrada")
                st.rerun()

    citas_filtradas = [c for c in citas_all if c.status in filtro_status]
    citas_filtradas.sort(key=lambda x: x.fecha)

    if not citas_filtradas:
        st.markdown('<div class="info-box">📭 No hay citas con los filtros seleccionados.</div>', unsafe_allow_html=True)
    else:
        for cita in citas_filtradas:
            colores_status = {"PENDIENTE":"🟡","CONFIRMADA":"🟢","CANCELADA":"🔴"}
            icono = colores_status.get(cita.status, "⚪")
            esHoy = cita.fecha.date() == hoy_str
            borde = "card-warn" if cita.status == "PENDIENTE" else ("card-green" if cita.status == "CONFIRMADA" else "card-red")

            with st.container():
                st.markdown(f'<div class="card {borde}">', unsafe_allow_html=True)
                c1, c2, c3, c4, c5 = st.columns([2.5, 1.8, 1.8, 1.2, 1.5])
                c1.markdown(f"**{cita.paciente.nombre or 'Sin nombre'}** {'⭐ HOY' if esHoy else ''}")
                c1.caption(f"📱 {cita.paciente.telefono}")
                c2.write(f"📅 {cita.fecha.strftime('%d/%m/%Y')}")
                c2.write(f"🕐 {cita.fecha.strftime('%H:%M')}")
                c3.write(f"📋 {cita.motivo}")
                c4.write(f"{icono} {cita.status}")

                with c5:
                    if cita.status == "PENDIENTE":
                        if st.button("✅", key=f"conf_{cita.id}", help="Confirmar cita", use_container_width=True):
                            run(db.cita.update(where={'id': cita.id}, data={'status': 'CONFIRMADA'}))
                            st.toast("✅ Cita confirmada")
                            st.rerun()
                    if cita.status != "CANCELADA":
                        if st.button("❌", key=f"canc_{cita.id}", help="Cancelar cita", use_container_width=True):
                            run(db.cita.update(where={'id': cita.id}, data={'status': 'CANCELADA'}))
                            st.toast("Cita cancelada")
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────
# TAB 2: PACIENTES
# ─────────────────────────────────────────────────
with tab_pacientes:
    st.subheader("👥 Gestión de Pacientes")

    col_bus, col_btn = st.columns([3, 1])
    with col_bus:
        buscar_pac = st.text_input("🔍 Buscar paciente por nombre o teléfono", placeholder="Escribe para buscar...")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        nuevo_pac = st.button("➕ Nuevo Paciente", use_container_width=True, type="primary")

    if nuevo_pac:
        with st.expander("📝 Registrar nuevo paciente", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                np_nombre   = st.text_input("Nombre completo *")
                np_tel      = st.text_input("Teléfono * (con código país: 521...)")
                np_email    = st.text_input("Email")
                np_fechanac = st.date_input("Fecha de nacimiento", value=date(1990,1,1))
            with c2:
                np_sexo     = st.selectbox("Sexo", ["Masculino","Femenino","No especificado"])
                np_tsangre  = st.selectbox("Tipo de sangre", ["—","A+","A-","B+","B-","AB+","AB-","O+","O-"])
                np_direccion= st.text_input("Dirección")
                np_alergias = st.text_area("Alergias conocidas", height=80)
            np_antec = st.text_area("Antecedentes médicos", placeholder="Enfermedades previas, cirugías, hospitalizaciones...")
            np_meds  = st.text_area("Medicamentos actuales", height=80)
            np_notas = st.text_area("Notas adicionales", height=60)

            if st.button("💾 Guardar paciente", type="primary"):
                if np_nombre and np_tel:
                    try:
                        run(db.paciente.create(data={
                            'nombre': np_nombre,
                            'telefono': np_tel,
                            'email': np_email or None,
                            'fechaNac': datetime.combine(np_fechanac, datetime.min.time()) if np_fechanac else None,
                            'sexo': np_sexo,
                            'tipoSangre': np_tsangre if np_tsangre != "—" else None,
                            'direccion': np_direccion or None,
                            'alergias': np_alergias or None,
                            'antecedentes': np_antec or None,
                            'medicamentos': np_meds or None,
                            'notas': np_notas or None
                        }))
                        st.success(f"✅ Paciente {np_nombre} registrado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e} (verifica que el teléfono no esté duplicado)")
                else:
                    st.error("Nombre y teléfono son obligatorios")

    # Lista de pacientes
    pacs = pacientes_all
    if buscar_pac:
        q = buscar_pac.lower()
        pacs = [p for p in pacs if q in (p.nombre or '').lower() or q in p.telefono]

    st.metric("Pacientes encontrados", len(pacs))

    for pac in pacs:
        edad_txt = ""
        if pac.fechaNac:
            edad = (date.today() - pac.fechaNac.date()).days // 365
            edad_txt = f"{edad} años"

        with st.expander(f"👤 {pac.nombre or 'Sin nombre'} · {pac.telefono} · {edad_txt}"):
            tab_info, tab_hist, tab_edit = st.tabs(["📋 Datos", "📜 Historial", "✏️ Editar"])

            with tab_info:
                c1, c2, c3 = st.columns(3)
                c1.metric("Sexo", pac.sexo or "—")
                c2.metric("Tipo de sangre", pac.tipoSangre or "—")
                c3.metric("Edad", edad_txt or "—")
                if pac.email:    st.write(f"📧 **Email:** {pac.email}")
                if pac.direccion: st.write(f"📍 **Dirección:** {pac.direccion}")
                if pac.alergias: st.markdown(f'<div class="warn-box">⚠️ <b>Alergias:</b> {pac.alergias}</div>', unsafe_allow_html=True)
                if pac.antecedentes: st.info(f"**Antecedentes:** {pac.antecedentes}")
                if pac.medicamentos: st.info(f"**Medicamentos actuales:** {pac.medicamentos}")
                if pac.notas: st.write(f"📝 **Notas:** {pac.notas}")

                citas_pac = [c for c in citas_all if c.pacienteId == pac.id]
                st.metric("Total de citas", len(citas_pac))

            with tab_hist:
                consultas_pac = run(db.consulta.find_many(
                    where={'pacienteId': pac.id},
                    order={'fecha': 'desc'}
                ))
                if not consultas_pac:
                    st.info("Sin consultas registradas")
                else:
                    for con in consultas_pac:
                        st.markdown(f"**📅 {con.fecha.strftime('%d/%m/%Y')}** — {con.motivo}")
                        if con.diagnostico: st.write(f"  🔍 Dx: {con.diagnostico}")
                        if con.receta: st.write(f"  💊 Rx: {con.receta[:80]}...")
                        st.markdown("---")

            with tab_edit:
                en_nombre = st.text_input("Nombre", value=pac.nombre or "", key=f"en_{pac.id}")
                ec1, ec2 = st.columns(2)
                with ec1:
                    en_email   = st.text_input("Email", value=pac.email or "", key=f"ee_{pac.id}")
                    en_alerg   = st.text_area("Alergias", value=pac.alergias or "", key=f"ea_{pac.id}", height=80)
                with ec2:
                    en_dir     = st.text_input("Dirección", value=pac.direccion or "", key=f"ed_{pac.id}")
                    en_meds    = st.text_area("Medicamentos", value=pac.medicamentos or "", key=f"em_{pac.id}", height=80)
                en_antec = st.text_area("Antecedentes", value=pac.antecedentes or "", key=f"eant_{pac.id}")
                en_notas = st.text_area("Notas", value=pac.notas or "", key=f"en2_{pac.id}", height=60)
                if st.button("💾 Guardar cambios", key=f"esave_{pac.id}", type="primary"):
                    run(db.paciente.update(where={'id': pac.id}, data={
                        'nombre': en_nombre or None,
                        'email': en_email or None,
                        'direccion': en_dir or None,
                        'alergias': en_alerg or None,
                        'antecedentes': en_antec or None,
                        'medicamentos': en_meds or None,
                        'notas': en_notas or None
                    }))
                    st.success("✅ Paciente actualizado")
                    st.rerun()

# ─────────────────────────────────────────────────
# TAB 3: CONSULTAS
# ─────────────────────────────────────────────────
with tab_consultas:
    st.subheader("🩺 Registro de Consultas")

    # Nueva consulta
    with st.expander("📝 Nueva consulta / Nota médica", expanded=False):
        if pacientes_all:
            pac_dict = {f"{p.nombre or p.telefono} ({p.telefono})": p for p in pacientes_all}
            pac_sel_con = st.selectbox("Paciente *", list(pac_dict.keys()), key="con_pac")
            pac_con = pac_dict[pac_sel_con]
        else:
            st.warning("No hay pacientes registrados.")
            pac_con = None

        if pac_con:
            # Mostrar alergias si las tiene
            if pac_con.alergias:
                st.markdown(f'<div class="warn-box">⚠️ <b>ALERGIAS:</b> {pac_con.alergias}</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                con_fecha   = st.date_input("Fecha consulta", value=date.today(), key="con_fecha")
                con_motivo  = st.text_input("Motivo de consulta", key="con_motivo")
                con_sint    = st.text_area("Síntomas / Exploración física", height=100, key="con_sint")
                con_dx      = st.text_input("Diagnóstico (CIE-10 opcional)", key="con_dx")
            with c2:
                con_tension = st.text_input("Tensión arterial (ej: 120/80)", key="con_ta")
                col_peso, col_talla = st.columns(2)
                with col_peso:
                    con_peso  = st.number_input("Peso (kg)", 0.0, 300.0, step=0.1, key="con_peso")
                with col_talla:
                    con_talla = st.number_input("Talla (cm)", 0.0, 250.0, step=0.5, key="con_talla")
                col_temp, col_glu = st.columns(2)
                with col_temp:
                    con_temp  = st.number_input("Temp °C", 30.0, 45.0, 36.5, step=0.1, key="con_temp")
                with col_glu:
                    con_glu   = st.number_input("Glucosa mg/dL", 0.0, step=1.0, key="con_glu")
                con_trat  = st.text_area("Tratamiento / Plan", height=100, key="con_trat")

            con_receta = st.text_area("Receta médica (una línea por medicamento)", height=100,
                                       placeholder="Ejemplo:\nAmoxicilina 500mg — 1 cápsula cada 8hrs por 7 días\nIbuprofeno 400mg — 1 tableta cada 6hrs si dolor",
                                       key="con_receta")
            con_obs    = st.text_area("Observaciones / Próxima cita", height=60, key="con_obs")

            cob_monto  = st.number_input("Cobro de esta consulta (MXN)", 0.0, value=CONSULTA_PRECIO, step=50.0, key="con_cobro")
            cob_metodo = st.selectbox("Método de pago", ["Efectivo","Transferencia","Tarjeta","Pendiente"], key="con_metodo")

            if st.button("💾 Guardar consulta", type="primary", key="btn_guardar_con"):
                if con_motivo:
                    try:
                        nueva_con = run(db.consulta.create(data={
                            'pacienteId': pac_con.id,
                            'fecha': datetime.combine(con_fecha, datetime.now().time()),
                            'motivo': con_motivo,
                            'sintomas': con_sint or None,
                            'diagnostico': con_dx or None,
                            'tratamiento': con_trat or None,
                            'receta': con_receta or None,
                            'tension': con_tension or None,
                            'peso': con_peso if con_peso > 0 else None,
                            'talla': con_talla if con_talla > 0 else None,
                            'temperatura': con_temp if con_temp > 0 else None,
                            'glucosa': con_glu if con_glu > 0 else None,
                            'observaciones': con_obs or None,
                        }))
                        if cob_monto > 0:
                            run(db.cobro.create(data={
                                'pacienteId': pac_con.id,
                                'consultaId': nueva_con.id,
                                'concepto': f"Consulta — {con_dx or con_motivo}",
                                'monto': cob_monto,
                                'pagado': cob_metodo != "Pendiente",
                                'metodoPago': cob_metodo if cob_metodo != "Pendiente" else None,
                                'fecha': datetime.now()
                            }))
                        st.success("✅ Consulta registrada correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("El motivo de consulta es obligatorio")

    st.markdown("---")
    st.subheader("Historial de consultas")

    filtro_pac_con = st.selectbox("Filtrar por paciente",
                                   ["Todos"] + [f"{p.nombre or p.telefono}" for p in pacientes_all],
                                   key="filtro_con_pac")

    try:
        consultas_all = run(db.consulta.find_many(
            include={'paciente': True},
            order={'fecha': 'desc'}
        ))
    except:
        consultas_all = []

    if filtro_pac_con != "Todos":
        consultas_all = [c for c in consultas_all
                         if (c.paciente.nombre or c.paciente.telefono) == filtro_pac_con]

    for con in consultas_all[:50]:
        with st.expander(f"🩺 {con.fecha.strftime('%d/%m/%Y')} — {con.paciente.nombre or con.paciente.telefono} — {con.motivo}"):
            c1, c2, c3, c4 = st.columns(4)
            if con.tension:     c1.metric("T/A", con.tension)
            if con.peso:        c2.metric("Peso", f"{con.peso} kg")
            if con.temperatura: c3.metric("Temp", f"{con.temperatura}°C")
            if con.glucosa:     c4.metric("Glucosa", f"{con.glucosa} mg/dL")
            if con.sintomas:    st.write(f"**Síntomas:** {con.sintomas}")
            if con.diagnostico: st.success(f"**Diagnóstico:** {con.diagnostico}")
            if con.tratamiento: st.write(f"**Tratamiento:** {con.tratamiento}")
            if con.receta:
                st.info(f"**Receta:** {con.receta}")
            if con.observaciones: st.write(f"**Observaciones:** {con.observaciones}")

# ─────────────────────────────────────────────────
# TAB 4: RECETAS
# ─────────────────────────────────────────────────
with tab_recetas:
    st.subheader("💊 Generador de Recetas Médicas")
    st.markdown('<div class="info-box">Genera recetas en PDF con membrete profesional listas para imprimir.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if pacientes_all:
            pac_dict_rx = {f"{p.nombre or p.telefono} ({p.telefono})": p for p in pacientes_all}
            pac_sel_rx  = st.selectbox("Paciente", list(pac_dict_rx.keys()), key="rx_pac")
            pac_rx      = pac_dict_rx[pac_sel_rx]
            edad_rx = ""
            if pac_rx.fechaNac:
                edad_rx = f"{(date.today() - pac_rx.fechaNac.date()).days // 365} años"
            if pac_rx.alergias:
                st.markdown(f'<div class="warn-box">⚠️ ALERGIAS: {pac_rx.alergias}</div>', unsafe_allow_html=True)
        else:
            st.warning("No hay pacientes registrados")
            pac_rx = None
            edad_rx = ""

        rx_dx    = st.text_input("Diagnóstico", key="rx_dx")
        rx_texto = st.text_area("Medicamentos (un renglón por medicamento)", height=200,
                                 placeholder="Amoxicilina 500mg — 1 cápsula cada 8hrs x 7 días\nIbuprofeno 400mg — 1 tableta c/8hrs si dolor\nOmeprazol 20mg — 1 cápsula en ayunas x 14 días",
                                 key="rx_texto")

    with c2:
        st.markdown("#### Vista previa de membrete")
        st.markdown(f"""
        <div style="border:2px solid #0891b2;border-radius:12px;padding:1rem;background:#f0f9ff">
            <div style="background:#0e7490;color:white;padding:0.8rem;border-radius:8px;margin-bottom:1rem">
                <b>{CLINIC_NAME}</b><br>
                <small>{DOCTOR_NAME} · {SPECIALTY}</small>
            </div>
            <b>Paciente:</b> {pac_rx.nombre if pac_rx else '—'} · {edad_rx}<br>
            <b>Diagnóstico:</b> {rx_dx or '—'}<br><br>
            <div style="font-size:2rem;color:#0e7490"><b>℞</b></div>
            <div style="margin-left:1rem;color:#374151">
                {rx_texto.replace(chr(10),'<br>') if rx_texto else '(medicamentos aquí)'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        rx_notas = st.text_area("Indicaciones generales", height=80,
                                  placeholder="Reposo relativo, abundante líquido, próxima cita en 7 días...",
                                  key="rx_notas")

    if st.button("📄 Generar Receta PDF", type="primary", use_container_width=True):
        if pac_rx and rx_texto:
            texto_completo = rx_texto
            if rx_notas:
                texto_completo += f"\n\n**Indicaciones:** {rx_notas}"
            pdf_buf = generar_receta_pdf(
                paciente_nombre=pac_rx.nombre or pac_rx.telefono,
                paciente_edad=edad_rx,
                diagnostico=rx_dx,
                receta_texto=texto_completo,
                doctor=DOCTOR_NAME,
                especialidad=SPECIALTY,
                clinica=CLINIC_NAME
            )
            st.download_button(
                "📥 Descargar Receta PDF",
                pdf_buf,
                f"Receta_{pac_rx.nombre or pac_rx.telefono}_{date.today().strftime('%Y%m%d')}.pdf",
                "application/pdf",
                use_container_width=True
            )
        else:
            st.error("Selecciona paciente y escribe los medicamentos")

    # Historial de recetas
    st.markdown("---")
    st.subheader("Recetas previas")
    try:
        recetas_prev = run(db.consulta.find_many(
            where={'receta': {'not': None}},
            include={'paciente': True},
            order={'fecha': 'desc'}
        ))
        for r in recetas_prev[:20]:
            if r.receta:
                with st.expander(f"💊 {r.fecha.strftime('%d/%m/%Y')} — {r.paciente.nombre or r.paciente.telefono}"):
                    st.write(f"**Dx:** {r.diagnostico or '—'}")
                    st.code(r.receta)
                    if st.button("🔄 Reutilizar esta receta", key=f"reuse_{r.id}"):
                        st.session_state['rx_prefill'] = r.receta
                        st.info("Copia la receta de arriba al generador")
    except:
        st.info("No hay recetas previas registradas")

# ─────────────────────────────────────────────────
# TAB 5: COBROS
# ─────────────────────────────────────────────────
with tab_cobros:
    st.subheader("💰 Control de Pagos y Cobros")

    # KPIs cobros
    total_cobrado   = sum(c.monto for c in cobros_all if c.pagado)
    total_pendiente = sum(c.monto for c in cobros_all if not c.pagado)
    cobros_mes      = [c for c in cobros_all if c.fecha.month == datetime.now().month and c.pagado]

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-green"><div class="kpi-val">${total_cobrado:,.0f}</div><div class="kpi-lbl">Total cobrado</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-amber"><div class="kpi-val">${total_pendiente:,.0f}</div><div class="kpi-lbl">Por cobrar</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-teal"><div class="kpi-val">${ingresos_mes:,.0f}</div><div class="kpi-lbl">Este mes</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-teal"><div class="kpi-val">{len(cobros_mes)}</div><div class="kpi-lbl">Cobros este mes</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Nuevo cobro manual
    with st.expander("➕ Registrar cobro manual"):
        if pacientes_all:
            pac_cob_dict = {f"{p.nombre or p.telefono}": p.id for p in pacientes_all}
            pac_cob_sel  = st.selectbox("Paciente", list(pac_cob_dict.keys()), key="cob_pac")
            cob_concepto = st.text_input("Concepto", value="Consulta médica", key="cob_concepto")
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                cob_monto_m = st.number_input("Monto (MXN)", 0.0, value=CONSULTA_PRECIO, step=50.0, key="cob_monto_m")
            with cc2:
                cob_metodo_m = st.selectbox("Método", ["Efectivo","Transferencia","Tarjeta"], key="cob_met_m")
            with cc3:
                cob_pagado_m = st.checkbox("¿Pagado?", value=True, key="cob_pag_m")
            if st.button("💾 Guardar cobro", key="btn_cob_man", type="primary"):
                run(db.cobro.create(data={
                    'pacienteId': pac_cob_dict[pac_cob_sel],
                    'concepto': cob_concepto,
                    'monto': cob_monto_m,
                    'pagado': cob_pagado_m,
                    'metodoPago': cob_metodo_m if cob_pagado_m else None,
                    'fecha': datetime.now()
                }))
                st.success("✅ Cobro registrado")
                st.rerun()

    # Lista de cobros pendientes
    st.subheader("Cobros pendientes")
    try:
        cobros_pend = run(db.cobro.find_many(
            where={'pagado': False},
            include={'paciente': True},
            order={'fecha': 'desc'}
        ))
    except:
        cobros_pend = []

    if not cobros_pend:
        st.markdown('<div class="card card-green">✅ No hay cobros pendientes — ¡todo al corriente!</div>', unsafe_allow_html=True)
    else:
        for cob in cobros_pend:
            c1, c2, c3, c4 = st.columns([2.5, 2, 1.5, 1.5])
            c1.write(f"**{cob.paciente.nombre or cob.paciente.telefono}**")
            c2.write(cob.concepto)
            c3.metric("", f"${cob.monto:,.0f}")
            with c4:
                if st.button("💵 Marcar pagado", key=f"pag_{cob.id}", use_container_width=True):
                    run(db.cobro.update(where={'id': cob.id}, data={'pagado': True, 'metodoPago': 'Efectivo'}))
                    st.toast("✅ Marcado como pagado")
                    st.rerun()

    st.markdown("---")
    st.subheader("Historial de cobros")
    filtro_mes_cob = st.selectbox("Mes",
                                   [datetime(2025, m, 1).strftime('%B %Y') for m in range(1,13)],
                                   index=datetime.now().month-1, key="filtro_mes_cob")
    mes_num = list(range(1,13))[["enero","febrero","marzo","abril","mayo","junio",
                                   "julio","agosto","septiembre","octubre","noviembre","diciembre"]
                                  .index(filtro_mes_cob.split()[0].lower())]
    try:
        cobros_hist = run(db.cobro.find_many(
            include={'paciente': True},
            order={'fecha': 'desc'}
        ))
        cobros_mes_fil = [c for c in cobros_hist if c.fecha.month == mes_num]
    except:
        cobros_mes_fil = []

    if cobros_mes_fil:
        df_cob = [{"Fecha": c.fecha.strftime('%d/%m'),"Paciente": c.paciente.nombre or c.paciente.telefono,
                   "Concepto": c.concepto,"Monto": f"${c.monto:,.0f}",
                   "Método": c.metodoPago or "—","Estado": "✅ Pagado" if c.pagado else "⏳ Pendiente"}
                  for c in cobros_mes_fil]
        import pandas as pd
        st.dataframe(pd.DataFrame(df_cob), use_container_width=True, hide_index=True)
        total_mes_fil = sum(c.monto for c in cobros_mes_fil if c.pagado)
        st.metric(f"Total cobrado en {filtro_mes_cob}", f"${total_mes_fil:,.2f}")
    else:
        st.info("Sin cobros en este periodo")

# ─────────────────────────────────────────────────
# TAB 6: INVENTARIO
# ─────────────────────────────────────────────────
with tab_inventario:
    st.subheader("📦 Inventario Médico")
    st.markdown('<div class="info-box">Controla medicamentos y material de curación. Recibe alertas cuando el stock baja del mínimo.</div>', unsafe_allow_html=True)

    # Agregar producto
    with st.expander("➕ Agregar medicamento / insumo"):
        ic1, ic2 = st.columns(2)
        with ic1:
            inv_nombre    = st.text_input("Nombre del producto *", key="inv_nom")
            inv_categoria = st.selectbox("Categoría", ["Medicamento","Material curación","Equipo","Otro"], key="inv_cat")
            inv_cantidad  = st.number_input("Cantidad actual", 0, step=1, key="inv_qty")
            inv_unidad    = st.text_input("Unidad", value="piezas", key="inv_und")
        with ic2:
            inv_minimo    = st.number_input("Stock mínimo (alerta)", 0, step=1, value=5, key="inv_min")
            inv_precio    = st.number_input("Precio unitario (MXN)", 0.0, step=1.0, key="inv_pre")
            inv_prov      = st.text_input("Proveedor", key="inv_prov")
            inv_venc      = st.date_input("Fecha de vencimiento", value=None, key="inv_venc")
        inv_notas = st.text_input("Notas", key="inv_notas")
        if st.button("💾 Guardar", type="primary", key="btn_inv_save"):
            if inv_nombre:
                try:
                    run(db.inventario.create(data={
                        'nombre': inv_nombre,
                        'categoria': inv_categoria,
                        'cantidad': inv_cantidad,
                        'unidad': inv_unidad,
                        'minimo': inv_minimo,
                        'precio': inv_precio if inv_precio > 0 else None,
                        'proveedor': inv_prov or None,
                        'vencimiento': datetime.combine(inv_venc, datetime.min.time()) if inv_venc else None,
                        'notas': inv_notas or None
                    }))
                    st.success(f"✅ {inv_nombre} agregado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("El nombre es obligatorio")

    # Listar inventario
    try:
        inventario_all = run(db.inventario.find_many(order={'nombre': 'asc'}))
    except:
        inventario_all = []

    if not inventario_all:
        st.info("📦 Inventario vacío. Agrega tus primeros productos arriba.")
    else:
        # Alertas de stock bajo
        bajo_stock = [i for i in inventario_all if i.cantidad <= i.minimo]
        if bajo_stock:
            st.markdown(f'<div class="warn-box">⚠️ <b>{len(bajo_stock)} productos</b> con stock bajo o agotado</div>', unsafe_allow_html=True)

        cat_filtro = st.selectbox("Categoría", ["Todas"] + list(set(i.categoria for i in inventario_all)), key="inv_cat_fil")
        items_show = inventario_all if cat_filtro == "Todas" else [i for i in inventario_all if i.categoria == cat_filtro]

        import pandas as pd
        hoy_inv = date.today()
        rows = []
        for item in items_show:
            venc_str = item.vencimiento.strftime('%d/%m/%Y') if item.vencimiento else "—"
            venc_alert = ""
            if item.vencimiento:
                dias_venc = (item.vencimiento.date() - hoy_inv).days
                if dias_venc < 0:       venc_alert = "🔴 VENCIDO"
                elif dias_venc <= 30:   venc_alert = f"⚠️ {dias_venc}d"
                else:                   venc_alert = f"✅ {dias_venc}d"
            stock_alert = "🔴" if item.cantidad == 0 else ("⚠️" if item.cantidad <= item.minimo else "✅")
            rows.append({
                "Producto": item.nombre,
                "Categoría": item.categoria,
                "Stock": f"{stock_alert} {item.cantidad} {item.unidad}",
                "Mínimo": item.minimo,
                "Precio": f"${item.precio:,.2f}" if item.precio else "—",
                "Vencimiento": f"{venc_str} {venc_alert}",
                "Proveedor": item.proveedor or "—"
            })

        df_inv = pd.DataFrame(rows)
        st.dataframe(df_inv, use_container_width=True, hide_index=True, height=350)

        # Actualizar stock
        st.markdown("#### Actualizar stock")
        item_dict = {i.nombre: i for i in items_show}
        item_sel  = st.selectbox("Producto a actualizar", list(item_dict.keys()), key="inv_upd_sel")
        item_obj  = item_dict[item_sel]
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            nuevo_qty = st.number_input(f"Nueva cantidad ({item_obj.unidad})", 0, value=item_obj.cantidad, key="inv_new_qty")
        with col_act2:
            st.markdown(f"<br>Stock actual: **{item_obj.cantidad} {item_obj.unidad}**", unsafe_allow_html=True)
        if st.button("💾 Actualizar stock", key="btn_inv_upd"):
            run(db.inventario.update(where={'id': item_obj.id}, data={'cantidad': nuevo_qty}))
            st.success(f"✅ Stock de {item_sel} actualizado a {nuevo_qty} {item_obj.unidad}")
            st.rerun()

# ─────────────────────────────────────────────────
# TAB 7: ESTADÍSTICAS
# ─────────────────────────────────────────────────
with tab_stats:
    st.subheader("📊 Estadísticas del Consultorio")

    import pandas as pd
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        PLOTLY = True
    except:
        PLOTLY = False

    if not citas_all:
        st.info("Sin datos suficientes para mostrar estadísticas.")
    else:
        # Citas por mes
        df_citas = pd.DataFrame([{
            'fecha': c.fecha,
            'mes': c.fecha.strftime('%Y-%m'),
            'status': c.status,
            'paciente_id': c.pacienteId
        } for c in citas_all])

        c1, c2 = st.columns(2)
        with c1:
            if PLOTLY:
                citas_mes = df_citas.groupby(['mes','status']).size().reset_index(name='cantidad')
                fig = px.bar(citas_mes, x='mes', y='cantidad', color='status',
                             title="Citas por mes",
                             color_discrete_map={'PENDIENTE':'#f59e0b','CONFIRMADA':'#10b981','CANCELADA':'#ef4444'})
                fig.update_layout(height=300, xaxis_title="", yaxis_title="Citas")
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            if PLOTLY:
                status_counts = df_citas['status'].value_counts().reset_index()
                status_counts.columns = ['Status','Cantidad']
                fig2 = px.pie(status_counts, names='Status', values='Cantidad',
                              title="Estado de citas",
                              color_discrete_map={'PENDIENTE':'#f59e0b','CONFIRMADA':'#10b981','CANCELADA':'#ef4444'})
                fig2.update_layout(height=300)
                st.plotly_chart(fig2, use_container_width=True)

        # Ingresos por mes
        if cobros_all:
            df_cobros_stats = pd.DataFrame([{
                'mes': c.fecha.strftime('%Y-%m'),
                'monto': c.monto,
                'pagado': c.pagado
            } for c in cobros_all])

            c3, c4 = st.columns(2)
            with c3:
                if PLOTLY:
                    ing_mes = df_cobros_stats[df_cobros_stats['pagado']].groupby('mes')['monto'].sum().reset_index()
                    ing_mes.columns = ['Mes','Ingresos']
                    fig3 = px.area(ing_mes, x='Mes', y='Ingresos',
                                   title="Ingresos mensuales (MXN)",
                                   color_discrete_sequence=['#0891b2'])
                    fig3.update_layout(height=300)
                    st.plotly_chart(fig3, use_container_width=True)

            with c4:
                total_cob_stats = df_cobros_stats[df_cobros_stats['pagado']]['monto'].sum()
                total_pen_stats = df_cobros_stats[~df_cobros_stats['pagado']]['monto'].sum()
                if PLOTLY:
                    fig4 = go.Figure(go.Pie(
                        values=[total_cob_stats, total_pen_stats],
                        labels=['Cobrado','Pendiente'],
                        hole=0.5,
                        marker_colors=['#10b981','#f59e0b']
                    ))
                    fig4.update_layout(title="Cobrado vs Pendiente", height=300)
                    st.plotly_chart(fig4, use_container_width=True)

        # Pacientes nuevos por mes
        if pacientes_all:
            df_pacs = pd.DataFrame([{'mes': p.createdAt.strftime('%Y-%m')} for p in pacientes_all])
            pacs_mes = df_pacs.groupby('mes').size().reset_index(name='nuevos')
            st.subheader("Pacientes nuevos por mes")
            if PLOTLY:
                fig5 = px.bar(pacs_mes, x='mes', y='nuevos', title="Nuevos pacientes por mes",
                              color_discrete_sequence=['#0891b2'])
                fig5.update_layout(height=250)
                st.plotly_chart(fig5, use_container_width=True)

        # Tabla resumen
        st.subheader("Resumen ejecutivo")
        resumen = {
            "Métrica": [
                "Total pacientes registrados",
                "Total citas en el sistema",
                "Citas confirmadas",
                "Citas canceladas",
                "Tasa de confirmación",
                "Ingresos totales",
                "Por cobrar",
                "Ticket promedio por consulta"
            ],
            "Valor": [
                f"{len(pacientes_all)}",
                f"{len(citas_all)}",
                f"{len([c for c in citas_all if c.status=='CONFIRMADA'])}",
                f"{len([c for c in citas_all if c.status=='CANCELADA'])}",
                f"{len([c for c in citas_all if c.status=='CONFIRMADA'])/max(len(citas_all),1)*100:.1f}%",
                f"${sum(c.monto for c in cobros_all if c.pagado):,.2f}",
                f"${sum(c.monto for c in cobros_all if not c.pagado):,.2f}",
                f"${sum(c.monto for c in cobros_all)/max(len(cobros_all),1):,.2f}"
            ]
        }
        st.dataframe(pd.DataFrame(resumen), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────
# TAB 8: WEBS SUGERIDAS
# ─────────────────────────────────────────────────
with tab_webs:
    st.subheader("🌐 Webs Sugeridas para Médicos")
    st.caption("Recursos útiles en línea para la práctica médica y gestión del consultorio.")

    WEBS_FIJAS = [
        {
            "nombre": "MedPanel Pro",
            "url": "https://consultorio-bot-9j3t.onrender.com/",
            "desc": "Tu sistema de gestión médica actual. Agendas, expedientes, recetas y estadísticas.",
            "emoji": "🏥"
        },
        {
            "nombre": "CIE-10 en Línea",
            "url": "https://cie10.com.mx/",
            "desc": "Clasificación Internacional de Enfermedades. Busca códigos de diagnóstico rápidamente.",
            "emoji": "📋"
        },
        {
            "nombre": "Vademécum Farmacológico",
            "url": "https://www.vademecum.es/",
            "desc": "Base de datos de medicamentos, presentaciones, dosis e interacciones farmacológicas.",
            "emoji": "💊"
        },
        {
            "nombre": "IMSS - Catálogo de Medicamentos",
            "url": "https://www.imss.gob.mx/salud-en-linea/catalogo-medicamentos",
            "desc": "Catálogo oficial de medicamentos del IMSS para prescripciones y referencias.",
            "emoji": "🏛️"
        },
        {
            "nombre": "Medscape",
            "url": "https://www.medscape.com/",
            "desc": "Noticias médicas, guías clínicas, calculadoras de dosis y educación continua.",
            "emoji": "🔬"
        },
        {
            "nombre": "UpToDate",
            "url": "https://www.uptodate.com/",
            "desc": "Evidencia clínica actualizada. Referencia de práctica médica basada en evidencia.",
            "emoji": "📖"
        },
        {
            "nombre": "SAT - RFC y Facturación",
            "url": "https://www.sat.gob.mx/",
            "desc": "Portal del SAT para emitir facturas electrónicas, declaraciones y trámites fiscales.",
            "emoji": "🧾"
        },
        {
            "nombre": "COFEPRIS",
            "url": "https://www.gob.mx/cofepris",
            "desc": "Comisión Federal para la Protección contra Riesgos Sanitarios. Regulación y permisos.",
            "emoji": "⚕️"
        },
        {
            "nombre": "Aventura con las Tablas Pro",
            "url": "https://aventura-tablas-pro.streamlit.app/",
            "desc": "App educativa para niños. Practica las tablas de multiplicar de forma divertida.",
            "emoji": "✏️"
        },
    ]

    if "webs_custom_med" not in st.session_state:
        st.session_state.webs_custom_med = []

    todas_webs = WEBS_FIJAS + st.session_state.webs_custom_med

    cols = st.columns(3)
    for i, w in enumerate(todas_webs):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#0d9488,#0f766e);border-radius:12px;padding:18px;margin-bottom:14px;color:white;">
                <div style="font-size:2rem">{w['emoji']}</div>
                <div style="font-weight:700;font-size:1rem;margin:6px 0">{w['nombre']}</div>
                <div style="font-size:0.82rem;opacity:0.9;margin-bottom:10px">{w['desc']}</div>
                <a href="{w['url']}" target="_blank"
                   style="background:rgba(255,255,255,0.2);color:white;padding:6px 14px;border-radius:20px;text-decoration:none;font-size:0.82rem;font-weight:600;">
                   🔗 Visitar
                </a>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("➕ Agregar web personalizada")
    with st.form("form_web_med"):
        wc1, wc2 = st.columns(2)
        with wc1:
            w_nombre = st.text_input("Nombre del sitio")
            w_url    = st.text_input("URL (https://...)")
        with wc2:
            w_emoji  = st.text_input("Emoji", value="🌐")
            w_desc   = st.text_area("Descripción corta", height=80)
        if st.form_submit_button("Agregar", type="primary"):
            if w_nombre and w_url:
                st.session_state.webs_custom_med.append({
                    "nombre": w_nombre, "url": w_url,
                    "desc": w_desc, "emoji": w_emoji
                })
                st.success(f"'{w_nombre}' agregada correctamente.")
                st.rerun()
            else:
                st.warning("Nombre y URL son obligatorios.")
