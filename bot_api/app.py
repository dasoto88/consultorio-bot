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

st.set_page_config(page_title="ConsultorioBot", page_icon="⚕️", layout="wide")

# ===== BASE DE DATOS =====
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
    
    # Super Admin
    c.execute("SELECT * FROM doctores WHERE email='admin@consultoriobot.com'")
    if not c.fetchone():
        c.execute("INSERT INTO doctores (id, nombre, email, licencia, password_hash, telefono, especialidad, activo, fecha_registro) VALUES (0, 'Super Admin', 'admin@consultoriobot.com', 'ADMIN-MASTER',?, '', 'Admin', 1,?)", 
                  (hash_password('admindasoto88'), str(datetime.now())))
    conn.commit()
    conn.close()

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def generar_licencia():
    return f"DOC-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

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

# ===== PDF REPORTES =====
def generar_pdf_reporte(df_citas, titulo):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height - 1*inch, f"Reporte: {titulo}")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 1.3*inch, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    y = height - 1.8*inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1*inch, y, "Fecha")
    c.drawString(2*inch, y, "Hora")
    c.drawString(2.8*inch, y, "Paciente")
    c.drawString(4.5*inch, y, "Telefono")
    c.drawString(5.8*inch, y, "Estatus")
    y -= 0.2*inch
    
    c.setFont("Helvetica", 8)
    for _, row in df_citas.iterrows():
        if y < 1*inch:
            c.showPage()
            y = height - 1*inch
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
    st.title("⚕️ ConsultorioBot")
    st.caption("Sistema de gestión para consultorios médicos")
    email = st.text_input("Email")
    clave = st.text_input("Licencia o Contraseña", type="password")
    
    if st.button("Entrar", type="primary", use_container_width=True):
        pwd_hash = hash_password(clave)
        df = query_db("SELECT * FROM doctores WHERE email=? AND (licencia=? OR password_hash=?) AND activo=1", (email, clave, pwd_hash))
        if not df.empty:
            st.session_state['user'] = {'rol': 'admin' if df.iloc[0]['id']==0 else 'doctor', 'nombre': df.iloc[0]['nombre'], 'id': df.iloc[0]['id'], 'email': df.iloc[0]['email']}
            st.rerun()
        
        df_sec = query_db("SELECT * FROM secretarias WHERE email=? AND password_hash=? AND activo=1", (email, pwd_hash))
        if not df_sec.empty:
            st.session_state['user'] = {'rol': 'secretaria', 'nombre': df_sec.iloc[0]['nombre'], 'id': df_sec.iloc[0]['id'], 'email': df_sec.iloc[0]['email']}
            st.rerun()
            
        st.error("Email o Licencia/Contraseña incorrectos")

# ===== GESTIÓN DE CITAS =====
def mostrar_agenda(doctor_id, es_admin=False):
    st.subheader("📅 Agenda de Citas")
    
    col1, col2, col3 = st.columns(3)
    fecha_inicio = col1.date_input("Desde", datetime.now() - timedelta(days=7))
    fecha_fin = col2.date_input("Hasta", datetime.now() + timedelta(days=30))
    estatus_filtro = col3.selectbox("Estatus", ["Todos", "Agendada", "Completada", "Cancelada"])
    
    query = "SELECT c.*, s.nombre as secretaria_nombre FROM citas c LEFT JOIN secretarias s ON c.secretaria_id=s.id WHERE c.doctor_id=? AND c.fecha BETWEEN? AND?"
    params = [doctor_id, str(fecha_inicio), str(fecha_fin)]
    if estatus_filtro!= "Todos":
        query += " AND c.estatus=?"
        params.append(estatus_filtro)
    query += " ORDER BY c.fecha DESC, c.hora DESC"
    
    df = query_db(query, params)
    
    if df.empty:
        st.info("No hay citas en el rango seleccionado")
        return df
    
    # Mostrar tabla con acciones
    for idx, row in df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2,2,3,2,2])
            col1.write(f"**{row['fecha']} {row['hora']}**")
            col2.write(row['paciente_nombre'])
            col3.write(f"{row['motivo'][:30]}...")
            col4.write(f"`{row['estatus']}`")
            
            with col5:
                if st.button("Editar", key=f"edit_{row['id']}"):
                    st.session_state['edit_cita'] = row['id']
                if st.button("Borrar", key=f"del_{row['id']}"):
                    st.session_state['del_cita'] = row['id']
            
            if st.session_state.get('edit_cita') == row['id']:
                with st.form(f"form_edit_{row['id']}"):
                    st.write("**Editar Cita**")
                    nueva_fecha = st.date_input("Fecha", datetime.strptime(row['fecha'], '%Y-%m-%d'))
                    nueva_hora = st.time_input("Hora", datetime.strptime(row['hora'], '%H:%M:%S').time())
                    nuevo_motivo = st.text_area("Motivo", row['motivo'])
                    nuevo_estatus = st.selectbox("Estatus", ["Agendada", "Completada", "Cancelada"], index=["Agendada", "Completada", "Cancelada"].index(row['estatus']))
                    
                    col_a, col_b = st.columns(2)
                    if col_a.form_submit_button("Guardar Cambios"):
                        if st.session_state.get('confirm_edit')!= row['id']:
                            st.session_state['confirm_edit'] = row['id']
                            st.warning("¿Estás seguro de guardar los cambios?")
                        else:
                            exec_db("UPDATE citas SET fecha=?, hora=?, motivo=?, estatus=? WHERE id=?", 
                                   (str(nueva_fecha), str(nueva_hora), nuevo_motivo, nuevo_estatus, row['id']))
                            st.success("Cita actualizada")
                            del st.session_state['edit_cita']
                            del st.session_state['confirm_edit']
                            st.rerun()
                    if col_b.form_submit_button("Cancelar"):
                        del st.session_state['edit_cita']
                        st.rerun()
            
            if st.session_state.get('del_cita') == row['id']:
                st.error(f"¿Seguro que quieres BORRAR la cita de {row['paciente_nombre']} del {row['fecha']}?")
                col_a, col_b = st.columns(2)
                if col_a.button("Sí, Borrar", key=f"conf_del_{row['id']}", type="primary"):
                    exec_db("DELETE FROM citas WHERE id=?", (row['id'],))
                    st.success("Cita eliminada")
                    del st.session_state['del_cita']
                    st.rerun()
                if col_b.button("No", key=f"cancel_del_{row['id']}"):
                    del st.session_state['del_cita']
                    st.rerun()
            st.divider()
    
    return df

def form_nueva_cita(doctor_id, secretaria_id=None):
    with st.form("nueva_cita", clear_on_submit=True):
        st.subheader("➕ Agendar Nueva Cita")
        col1, col2 = st.columns(2)
        paciente = col1.text_input("Nombre paciente*")
        telefono = col2.text_input("WhatsApp paciente*", placeholder="521633...")
        fecha = st.date_input("Fecha*")
        hora = st.time_input("Hora*")
        motivo = st.text_area("Motivo de consulta")
        
        if st.form_submit_button("Agendar Cita", type="primary"):
            if paciente and telefono:
                exec_db("INSERT INTO citas (doctor_id, secretaria_id, paciente_nombre, paciente_telefono, fecha, hora, motivo, estatus, origen, fecha_creacion) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (doctor_id, secretaria_id, paciente, telefono, str(fecha), str(hora), motivo, 'Agendada', 'Manual', str(datetime.now())))
                st.success(f"Cita agendada para {paciente}")
                st.rerun()
            else:
                st.error("Nombre y teléfono son obligatorios")

# ===== REPORTES =====
def mostrar_reportes(doctor_id):
    st.subheader("📊 Reportes")
    col1, col2 = st.columns(2)
    tipo = col1.selectbox("Periodo", ["Esta Semana", "Este Mes", "Este Año", "Personalizado"])
    
    if tipo == "Esta Semana":
        inicio = datetime.now() - timedelta(days=datetime.now().weekday())
        fin = inicio + timedelta(days=6)
    elif tipo == "Este Mes":
        inicio = datetime.now().replace(day=1)
        fin = (inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif tipo == "Este Año":
        inicio = datetime.now().replace(month=1, day=1)
        fin = datetime.now().replace(month=12, day=31)
    else:
        inicio = col1.date_input("Desde", datetime.now() - timedelta(days=30))
        fin = col2.date_input("Hasta", datetime.now())
    
    df = query_db("SELECT * FROM citas WHERE doctor_id=? AND fecha BETWEEN? AND? ORDER BY fecha, hora", 
                 (doctor_id, str(inicio.date() if isinstance(inicio, datetime) else inicio), str(fin.date() if isinstance(fin, datetime) else fin)))
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Citas", len(df))
    col2.metric("Agendadas", len(df[df['estatus']=='Agendada']))
    col3.metric("Completadas", len(df[df['estatus']=='Completada']))
    col4.metric("Canceladas", len(df[df['estatus']=='Cancelada']))
    
    st.dataframe(df[['fecha','hora','paciente_nombre','motivo','estatus']], use_container_width=True)
    
    if not df.empty:
        pdf = generar_pdf_reporte(df, f"{inicio} a {fin}")
        st.download_button("📥 Descargar PDF", pdf, f"reporte_{inicio}_{fin}.pdf", "application/pdf")

# ===== PANEL DOCTOR =====
def panel_doctor():
    doctor_id = st.session_state['user']['id']
    st.title(f"👨‍⚕️ Dr. {st.session_state['user']['nombre']}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Agenda", "Nueva Cita", "Secretarias", "Reportes"])
    
    with tab1:
        mostrar_agenda(doctor_id)
    with tab2:
        form_nueva_cita(doctor_id)
    with tab3:
        st.subheader("👥 Mis Secretarias")
        df_secs = query_db("SELECT s.* FROM secretarias s JOIN doctor_secretaria ds ON s.id=ds.secretaria_id WHERE ds.doctor_id=?", (doctor_id,))
        st.dataframe(df_secs[['nombre','email','activo']], use_container_width=True)
        
        with st.expander("➕ Agregar Secretaria"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Crear Nueva**")
                with st.form("nueva_sec"):
                    nombre = st.text_input("Nombre")
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Crear y Asignar"):
                        try:
                            sec_id = exec_db("INSERT INTO secretarias (nombre, email, password_hash, activo) VALUES (?,?,?,1)",
                                           (nombre, email, hash_password(password)))
                            exec_db("INSERT INTO doctor_secretaria VALUES (?,?)", (doctor_id, sec_id))
                            st.success(f"Secretaria {nombre} creada y asignada")
                            st.rerun()
                        except:
                            st.error("Ese email ya existe")
            with col2:
                st.write("**Asignar Existente**")
                df_todas = query_db("SELECT * FROM secretarias WHERE id NOT IN (SELECT secretaria_id FROM doctor_secretaria WHERE doctor_id=?)", (doctor_id,))
                if not df_todas.empty:
                    sec_sel = st.selectbox("Selecciona secretaria", df_todas['nombre'].tolist())
                    if st.button("Asignar a mi consultorio"):
                        sec_id = df_todas[df_todas['nombre']==sec_sel].iloc[0]['id']
                        exec_db("INSERT INTO doctor_secretaria VALUES (?,?)", (doctor_id, sec_id))
                        st.success(f"{sec_sel} asignada")
                        st.rerun()
                else:
                    st.info("No hay secretarias disponibles")
    
    with tab3:
        df_secs = query_db("SELECT s.* FROM secretarias s JOIN doctor_secretaria ds ON s.id=ds.secretaria_id WHERE ds.doctor_id=?", (doctor_id,))
        for _, sec in df_secs.iterrows():
            col1, col2 = st.columns([4,1])
            col1.write(f"**{sec['nombre']}** - {sec['email']}")
            if col2.button("Quitar", key=f"quit_{sec['id']}"):
                exec_db("DELETE FROM doctor_secretaria WHERE doctor_id=? AND secretaria_id=?", (doctor_id, sec['id']))
                st.rerun()
    
    with tab4:
        mostrar_reportes(doctor_id)

# ===== PANEL SECRETARIA =====
def panel_secretaria():
    sec_id = st.session_state['user']['id']
    # Buscar doctores asignados
    df_docs = query_db("SELECT d.* FROM doctores d JOIN doctor_secretaria ds ON d.id=ds.doctor_id WHERE ds.secretaria_id=?", (sec_id,))
    
    if df_docs.empty:
        st.error("No estás asignada a ningún doctor. Pide al doctor que te agregue.")
        return
    
    doc_sel = st.selectbox("Seleccionar Doctor", df_docs['nombre'].tolist())
    doctor_id = df_docs[df_docs['nombre']==doc_sel].iloc[0]['id']
    
    st.title(f"📋 Secretaria: {st.session_state['user']['nombre']}")
    st.caption(f"Consultorio: Dr. {doc_sel}")
    
    tab1, tab2 = st.tabs(["Agenda", "Nueva Cita"])
    with tab1:
        mostrar_agenda(doctor_id)
    with tab2:
        form_nueva_cita(doctor_id, sec_id)

# ===== PANEL SUPER ADMIN =====
def panel_admin():
    st.title("🔐 Panel Super Admin")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Doctores", "Nuevo Doctor", "Agendas", "Reportes Globales"])
    
    with tab1:
        st.subheader("Doctores Registrados")
        df = query_db("SELECT id, nombre, email, licencia, telefono, especialidad, activo FROM doctores WHERE id!=0")
        st.dataframe(df, use_container_width=True)
        
        st.subheader("Secretarias por Doctor")
        for _, doc in df.iterrows():
            with st.expander(f"Dr. {doc['nombre']}"):
                df_secs = query_db("SELECT s.nombre, s.email FROM secretarias s JOIN doctor_secretaria ds ON s.id=ds.secretaria_id WHERE ds.doctor_id=?", (doc['id'],))
                st.dataframe(df_secs, use_container_width=True)
    
    with tab2:
        with st.form("nuevo_doc"):
            nombre = st.text_input("Nombre completo del Doctor*")
            email = st.text_input("Email*")
            telefono = st.text_input("WhatsApp", placeholder="5216331124596")
            especialidad = st.text_input("Especialidad")
            if st.form_submit_button("Generar Licencia y Crear Doctor", type="primary"):
                licencia = generar_licencia()
                try:
                    exec_db("INSERT INTO doctores (nombre, email, licencia, password_hash, telefono, especialidad, activo, fecha_registro) VALUES (?,?,?,?,?,?,1,?)",
                           (nombre, email, licencia, '', telefono, especialidad, str(datetime.now())))
                    st.success(f"Doctor {nombre} creado")
                    st.code(f"Email: {email}\nLicencia: {licencia}", language=None)
                    st.info("El doctor puede entrar con estos datos. Puede cambiar la licencia por contraseña después.")
                except:
                    st.error("Ese email ya existe")
    
    with tab3:
        st.subheader("Ver Agenda de Doctor")
        df_docs = query_db("SELECT id, nombre FROM doctores WHERE id!=0")
        if not df_docs.empty:
            doc_sel = st.selectbox("Selecciona Doctor", df_docs['nombre'].tolist(), key="admin_doc")
            doctor_id = df_docs[df_docs['nombre']==doc_sel].iloc[0]['id']
            
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(f"**Gestionando agenda de: Dr. {doc_sel}**")
            with col2:
                if st.button("➕ Agendar por Doctor"):
                    st.session_state['admin_agendar'] = doctor_id
            
            if st.session_state.get('admin_agendar') == doctor_id:
                form_nueva_cita(doctor_id)
                if st.button("Cerrar Formulario"):
                    del st.session_state['admin_agendar']
                    st.rerun()
            
            mostrar_agenda(doctor_id, es_admin=True)
    
    with tab4:
        st.subheader("Reportes de Doctor")
        df_docs = query_db("SELECT id, nombre FROM doctores WHERE id!=0")
        if not df_docs.empty:
            doc_sel = st.selectbox("Selecciona Doctor", df_docs['nombre'].tolist(), key="admin_rep")
            doctor_id = df_docs[df_docs['nombre']==doc_sel].iloc[0]['id']
            mostrar_reportes(doctor_id)

# ===== MAIN =====
if 'user' not in st.session_state:
    login()
else:
    st.sidebar.write(f"**{st.session_state['user']['nombre']}**")
    st.sidebar.caption(st.session_state['user']['email'])
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        del st.session_state['user']
        st.rerun()
    
    rol = st.session_state['user']['rol']
    if rol == 'admin': panel_admin()
    elif rol == 'doctor': panel_doctor()
    elif rol == 'secretaria': panel_secretaria()
