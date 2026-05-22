import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import random
import string
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

st.set_page_config(page_title="ConsultorioBot Pro", page_icon="⚕️", layout="wide", initial_sidebar_state="expanded")

# ===== CSS PREMIUM =====
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {font-family: 'Poppins', sans-serif;}
    
   .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
   .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
        transition: transform 0.3s;
    }
   .metric-card:hover {transform: translateY(-5px);}
    
   .cita-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    
   .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
   .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
   .banner {
        background: url('https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=1200&q=80');
        background-size: cover;
        background-position: center;
        height: 200px;
        border-radius: 15px;
        margin-bottom: 2rem;
        position: relative;
    }
   .banner-overlay {
        background: rgba(102, 126, 234, 0.85);
        height: 100%;
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ===== DB =====
def init_db():
    conn = sqlite3.connect('consultorio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS doctores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, email TEXT UNIQUE, licencia TEXT UNIQUE, 
                  password_hash TEXT, telefono TEXT, especialidad TEXT, activo INTEGER, fecha_registro TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS secretarias
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, email TEXT UNIQUE, password_hash TEXT, activo INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS doctor_secretaria
                 (doctor_id INTEGER, secretaria_id INTEGER, PRIMARY KEY (doctor_id, secretaria_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS citas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_id INTEGER, secretaria_id INTEGER, paciente_nombre TEXT, 
                  paciente_telefono TEXT, fecha TEXT, hora TEXT, motivo TEXT, estatus TEXT, origen TEXT, fecha_creacion TEXT)''')
    
    c.execute("SELECT * FROM doctores WHERE email='dasoto88122911@gmail.com'")
    if not c.fetchone():
        c.execute("INSERT INTO doctores (id, nombre, email, licencia, password_hash, telefono, especialidad, activo, fecha_registro) VALUES (0, 'Super Admin', 'dasoto88122911@gmail.com', 'ADMIN-MASTER',?, '', 'Admin', 1,?)", 
                  (hash_password('admindasoto88'), str(datetime.now())))
    conn.commit()
    conn.close()

def hash_password(pwd): return hashlib.sha256(pwd.encode()).hexdigest()
def generar_licencia(): return f"DOC-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

def query_db(query, params=()):
    conn = sqlite3.connect('consultorio.db')
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def exec_db(query, params=()):
    conn = sqlite3.connect('consultorio.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    return last_id

init_db()

# ===== PDF =====
def generar_pdf(df_citas, titulo):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1*inch, height - 1*inch, f"ConsultorioBot Pro - {titulo}")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 1.3*inch, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y = height - 1.8*inch
    c.setFont("Helvetica-Bold", 9)
    for col, x in zip(['Fecha','Hora','Paciente','Telefono','Estatus'], [1,2,2.8,4.5,5.8]): c.drawString(x*inch, y, col)
    y -= 0.2*inch
    c.setFont("Helvetica", 8)
    for _, row in df_citas.iterrows():
        if y < 1*inch: c.showPage(); y = height - 1*inch
        c.drawString(1*inch, y, str(row['fecha']))
        c.drawString(2*inch, y, str(row['hora']))
        c.drawString(2.8*inch, y, str(row['paciente_nombre'])[:25])
        c.drawString(4.5*inch, y, str(row['paciente_telefono']))
        c.drawString(5.8*inch, y, str(row['estatus']))
        y -= 0.18*inch
    c.save()
    buffer.seek(0)
    return buffer

# ===== LOGIN =====
def login():
    st.markdown('<div class="banner"><div class="banner-overlay">⚕️ ConsultorioBot Pro</div></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="main-header"><h2 style="text-align:center;margin:0;">Sistema de Gestión Médica</h2><p style="text-align:center;margin:0;">Tecnología de última generación para tu consultorio</p></div>', unsafe_allow_html=True)
        email = st.text_input("📧 Email", placeholder="doctor@consultorio.com")
        clave = st.text_input("🔐 Licencia o Contraseña", type="password", placeholder="DOC-XXXX-XXXX")
        
        if st.button("Entrar al Sistema", type="primary", use_container_width=True):
            pwd_hash = hash_password(clave)
            df = query_db("SELECT * FROM doctores WHERE email=? AND (licencia=? OR password_hash=?) AND activo=1", (email, clave, pwd_hash))
            if not df.empty:
                st.session_state['user'] = {'rol': 'admin' if df.iloc[0]['id']==0 else 'doctor', 'nombre': df.iloc[0]['nombre'], 'id': df.iloc[0]['id'], 'email': df.iloc[0]['email']}
                st.rerun()
            df_sec = query_db("SELECT * FROM secretarias WHERE email=? AND password_hash=? AND activo=1", (email, pwd_hash))
            if not df_sec.empty:
                st.session_state['user'] = {'rol': 'secretaria', 'nombre': df_sec.iloc[0]['nombre'], 'id': df_sec.iloc[0]['id'], 'email': df_sec.iloc[0]['email']}
                st.rerun()
            st.error("❌ Credenciales incorrectas")

# ===== COMPONENTES =====
def mostrar_agenda(doctor_id):
    col1, col2, col3, col4 = st.columns(4)
    fecha_inicio = col1.date_input("Desde", datetime.now() - timedelta(days=7))
    fecha_fin = col2.date_input("Hasta", datetime.now() + timedelta(days=30))
    estatus_filtro = col3.selectbox("Filtrar", ["Todos", "Agendada", "Completada", "Cancelada"])
    
    query = "SELECT c.*, s.nombre as secretaria FROM citas c LEFT JOIN secretarias s ON c.secretaria_id=s.id WHERE c.doctor_id=? AND c.fecha BETWEEN? AND?"
    params = [doctor_id, str(fecha_inicio), str(fecha_fin)]
    if estatus_filtro!= "Todos": query += " AND c.estatus=?"; params.append(estatus_filtro)
    df = query_db(query + " ORDER BY c.fecha DESC, c.hora DESC", params)
    
    if df.empty: st.info("📅 No hay citas en el rango seleccionado"); return df
    
    for _, row in df.iterrows():
        with st.container():
            st.markdown(f'<div class="cita-card">', unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns([2,2,3,2,2])
            c1.markdown(f"**📅 {row['fecha']}**<br>🕐 {row['hora']}", unsafe_allow_html=True)
            c2.markdown(f"**👤 {row['paciente_nombre']}**<br>📱 {row['paciente_telefono']}", unsafe_allow_html=True)
            c3.write(f"📝 {row['motivo'][:40]}...")
            c4.markdown(f"**Estado:** `{row['estatus']}`<br>**Origen:** {row['origen']}", unsafe_allow_html=True)
            
            with c5:
                if st.button("✏️", key=f"edit_{row['id']}", help="Editar"): st.session_state['edit_cita'] = row['id']
                if st.button("🗑️", key=f"del_{row['id']}", help="Borrar"): st.session_state['del_cita'] = row['id']
            
            if st.session_state.get('edit_cita') == row['id']:
                with st.form(f"form_edit_{row['id']}", clear_on_submit=True):
                    st.write("**Editar Cita**")
                    nf = st.date_input("Fecha", datetime.strptime(row['fecha'], '%Y-%m-%d'))
                    nh = st.time_input("Hora", datetime.strptime(row['hora'], '%H:%M:%S').time())
                    nm = st.text_area("Motivo", row['motivo'])
                    ne = st.selectbox("Estatus", ["Agendada", "Completada", "Cancelada"], index=["Agendada", "Completada", "Cancelada"].index(row['estatus']))
                    if st.form_submit_button("💾 Guardar", type="primary"):
                        if st.session_state.get('confirm_edit')!= row['id']:
                            st.session_state['confirm_edit'] = row['id']; st.warning("⚠️ ¿Confirmar cambios?")
                        else:
                            exec_db("UPDATE citas SET fecha=?, hora=?, motivo=?, estatus=? WHERE id=?", (str(nf), str(nh), nm, ne, row['id']))
                            st.success("✅ Actualizada"); del st.session_state['edit_cita']; del st.session_state['confirm_edit']; st.rerun()
            
            if st.session_state.get('del_cita') == row['id']:
                st.error(f"⚠️ ¿Borrar cita de {row['paciente_nombre']} del {row['fecha']}?")
                ca, cb = st.columns(2)
                if ca.button("Sí, Borrar", key=f"conf_del_{row['id']}", type="primary"):
                    exec_db("DELETE FROM citas WHERE id=?", (row['id'],)); st.success("✅ Eliminada"); del st.session_state['del_cita']; st.rerun()
                if cb.button("Cancelar"): del st.session_state['del_cita']; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    return df

def form_cita(doctor_id, secretaria_id=None):
    with st.form("nueva_cita", clear_on_submit=True):
        st.subheader("➕ Nueva Cita")
        c1, c2 = st.columns(2)
        paciente = c1.text_input("Nombre paciente*", placeholder="Juan Pérez")
        telefono = c2.text_input("WhatsApp*", placeholder="5216331234567")
        fecha = st.date_input("Fecha*")
        hora = st.time_input("Hora*")
        motivo = st.text_area("Motivo", placeholder="Consulta general, revisión...")
        if st.form_submit_button("📅 Agendar Cita", type="primary", use_container_width=True):
            if paciente and telefono:
                exec_db("INSERT INTO citas (doctor_id, secretaria_id, paciente_nombre, paciente_telefono, fecha, hora, motivo, estatus, origen, fecha_creacion) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (doctor_id, secretaria_id, paciente, telefono, str(fecha), str(hora), motivo, 'Agendada', 'Manual', str(datetime.now())))
                st.success(f"✅ Cita agendada para {paciente}"); st.balloons()
            else: st.error("❌ Nombre y teléfono obligatorios")

def mostrar_reportes(doctor_id):
    c1, c2 = st.columns(2)
    tipo = c1.selectbox("📊 Periodo", ["Esta Semana", "Este Mes", "Este Año", "Personalizado"])
    if tipo == "Esta Semana": inicio = datetime.now() - timedelta(days=datetime.now().weekday()); fin = inicio + timedelta(days=6)
    elif tipo == "Este Mes": inicio = datetime.now().replace(day=1); fin = (inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif tipo == "Este Año": inicio = datetime.now().replace(month=1, day=1); fin = datetime.now().replace(month=12, day=31)
    else: inicio = c1.date_input("Desde", datetime.now() - timedelta(days=30)); fin = c2.date_input("Hasta", datetime.now())
    
    df = query_db("SELECT * FROM citas WHERE doctor_id=? AND fecha BETWEEN? AND? ORDER BY fecha, hora", 
                 (doctor_id, str(inicio.date() if isinstance(inicio, datetime) else inicio), str(fin.date() if isinstance(fin, datetime) else fin)))
    
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div class="metric-card"><h3>{len(df)}</h3><p>Total Citas</p></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><h3>{len(df[df["estatus"]=="Agendada"])}</h3><p>Agendadas</p></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><h3>{len(df[df["estatus"]=="Completada"])}</h3><p>Completadas</p></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-card"><h3>{len(df[df["estatus"]=="Cancelada"])}</h3><p>Canceladas</p></div>', unsafe_allow_html=True)
    
    st.dataframe(df[['fecha','hora','paciente_nombre','motivo','estatus','origen']], use_container_width=True)
    if not df.empty:
        pdf = generar_pdf(df, f"{inicio} a {fin}")
        st.download_button("📥 Descargar PDF", pdf, f"reporte_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)

# ===== PANELES =====
def panel_doctor():
    doctor_id = st.session_state['user']['id']
    st.markdown(f'<div class="main-header"><h1>👨‍⚕️ Dr. {st.session_state["user"]["nombre"]}</h1><p>Panel de Control Médico</p></div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 Agenda", "➕ Nueva Cita", "👥 Secretarias", "📊 Reportes"])
    with tab1: mostrar_agenda(doctor_id)
    with tab2: form_cita(doctor_id)
    with tab3:
        st.subheader("👥 Mis Secretarias")
        df_secs = query_db("SELECT s.* FROM secretarias s JOIN doctor_secretaria ds ON s.id=ds.secretaria_id WHERE ds.doctor_id=?", (doctor_id,))
        if not df_secs.empty:
            for _, sec in df_secs.iterrows():
                c1, c2 = st.columns([4,1])
                c1.markdown(f'<div class="cita-card"><b>{sec["nombre"]}</b><br>{sec["email"]}</div>', unsafe_allow_html=True)
                if c2.button("Quitar", key=f"quit_{sec['id']}"): exec_db("DELETE FROM doctor_secretaria WHERE doctor_id=? AND secretaria_id=?", (doctor_id, sec['id'])); st.rerun()
        
        with st.expander("➕ Agregar Secretaria"):
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Crear Nueva**")
                with st.form("nueva_sec", clear_on_submit=True):
                    nombre = st.text_input("Nombre")
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Crear", type="primary"):
                        try:
                            sec_id = exec_db("INSERT INTO secretarias (nombre, email, password_hash, activo) VALUES (?,?,?,1)", (nombre, email, hash_password(password)))
                            exec_db("INSERT INTO doctor_secretaria VALUES (?,?)", (doctor_id, sec_id))
                            st.success(f"✅ {nombre} agregada")
                        except: st.error("❌ Email ya existe")
            with c2:
                st.write("**Asignar Existente**")
                df_todas = query_db("SELECT * FROM secretarias WHERE id NOT IN (SELECT secretaria_id FROM doctor_secretaria WHERE doctor_id=?)", (doctor_id,))
                if not df_todas.empty:
                    sec_sel = st.selectbox("Selecciona", df_todas['nombre'].tolist())
                    if st.button("Asignar", type="primary", use_container_width=True):
                        sec_id = df_todas[df_todas['nombre']==sec_sel].iloc[0]['id']
                        exec_db("INSERT INTO doctor_secretaria VALUES (?,?)", (doctor_id, sec_id))
                        st.success(f"✅ {sec_sel} asignada"); st.rerun()
                else: st.info("No hay secretarias disponibles")
    with tab4: mostrar_reportes(doctor_id)

def panel_secretaria():
    sec_id = st.session_state['user']['id']
    df_docs = query_db("SELECT d.* FROM doctores d JOIN doctor_secretaria ds ON d.id=ds.doctor_id WHERE ds.secretaria_id=?", (sec_id,))
    if df_docs.empty: st.error("No estás asignada a ningún doctor"); return
    doc_sel = st.selectbox("👨‍⚕️ Consultorio", df_docs['nombre'].tolist())
    doctor_id = df_docs[df_docs['nombre']==doc_sel].iloc[0]['id']
    st.markdown(f'<div class="main-header"><h1>📋 {st.session_state["user"]["nombre"]}</h1><p>Consultorio: Dr. {doc_sel}</p></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📅 Agenda", "➕ Nueva Cita"])
    with tab1: mostrar_agenda(doctor_id)
    with tab2: form_cita(doctor_id, sec_id)

def panel_admin():
    st.markdown('<div class="main-header"><h1>🔐 Super Admin - ConsultorioBot Pro</h1><p>Control Total del Sistema</p></div>', unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["👨‍⚕️ Doctores", "➕ Nuevo Doctor", "📅 Agendas", "📊 Reportes"])
    
    with tab1:
        df = query_db("SELECT id, nombre, email, licencia, telefono, especialidad, activo FROM doctores WHERE id!=0")
        st.dataframe(df, use_container_width=True)
        for _, doc in df.iterrows():
            with st.expander(f"👨‍⚕️ Dr. {doc['nombre']} - {doc['email']}"):
                df_secs = query_db("SELECT s.nombre, s.email FROM secretarias s JOIN doctor_secretaria ds ON s.id=ds.secretaria_id WHERE ds.doctor_id=?", (doc['id'],))
                st.write("**Secretarias:**"); st.dataframe(df_secs, use_container_width=True)
    
    with tab2:
        with st.form("nuevo_doc", clear_on_submit=True):
            st.subheader("Crear Nuevo Doctor")
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre completo*")
            email = c2.text_input("Email*")
            telefono = c1.text_input("WhatsApp", placeholder="5216331234567")
            especialidad = c2.text_input("Especialidad", placeholder="Cardiología")
            if st.form_submit_button("🎫 Generar Licencia", type="primary", use_container_width=True):
                licencia = generar_licencia()
                try:
                    exec_db("INSERT INTO doctores (nombre, email, licencia, password_hash, telefono, especialidad, activo, fecha_registro) VALUES (?,?,?,?,?,?,1,?)",
                           (nombre, email, licencia, '', telefono, especialidad, str(datetime.now())))
                    st.success(f"✅ Doctor creado"); st.code(f"Email: {email}\nLicencia: {licencia}"); st.balloons()
                except: st.error("❌ Email ya existe")
    
    with tab3:
        df_docs = query_db("SELECT id, nombre FROM doctores WHERE id!=0")
        if not df_docs.empty:
            doc_sel = st.selectbox("Selecciona Doctor", df_docs['nombre'].tolist(), key="admin_doc")
            doctor_id = df_docs[df_docs['nombre']==doc_sel].iloc[0]['id']
            st.info(f"Gestionando: Dr. {doc_sel}")
            if st.button("➕ Agendar como Admin"): st.session_state['admin_agendar'] = doctor_id
            if st.session_state.get('admin_agendar') == doctor_id:
                form_cita(doctor_id)
                if st.button("Cerrar"): del st.session_state['admin_agendar']; st.rerun()
            mostrar_agenda(doctor_id)
    
    with tab4:
        df_docs = query_db("SELECT id, nombre FROM doctores WHERE id!=0")
        if not df_docs.empty:
            doc_sel = st.selectbox("Doctor", df_docs['nombre'].tolist(), key="admin_rep")
            doctor_id = df_docs[df_docs['nombre']==doc_sel].iloc[0]['id']
            mostrar_reportes(doctor_id)

# ===== MAIN =====
if 'user' not in st.session_state:
    login()
else:
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/stethoscope.png", width=80)
        st.markdown(f"### {st.session_state['user']['nombre']}")
        st.caption(st.session_state['user']['email'])
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            del st.session_state['user']; st.rerun()
        st.markdown("---")
        st.caption("**ConsultorioBot Pro v2.0**")
        st.caption("Tecnología médica de élite")
    
    rol = st.session_state['user']['rol']
    if rol == 'admin': panel_admin()
    elif rol == 'doctor': panel_doctor()
    elif rol == 'secretaria': panel_secretaria()
