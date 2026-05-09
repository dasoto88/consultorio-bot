import streamlit as st
import asyncio
from prisma import Prisma
from datetime import datetime, timedelta, date
import bcrypt
import requests
import os
import pandas as pd
import plotly.express as px
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

st.set_page_config(page_title="Consultorio Pro SaaS", layout="wide", page_icon="🏥")

# CSS PRO PARA QUE SE VEA DE AGENCIA
st.markdown("""
<style>
.main > div {padding-top: 2rem;}
.stButton>button {border-radius: 8px; font-weight: 600;}
.st-emotion-cache-1y4p8pa {padding: 1rem 1rem 10rem;}
h1 {font-weight: 800;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_db():
    db = Prisma()
    asyncio.run(db.connect())
    return db

db = init_db()

def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(password, hashed): return bcrypt.checkpw(password.encode(), hashed.encode())

def send_whatsapp(phone_id, to, text):
    token = os.getenv('MASTER_WHATSAPP_TOKEN')
    requests.post(f"https://graph.facebook.com/v20.0/{phone_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
    )

# SESIÓN
if 'role' not in st.session_state: st.session_state.role = None

# LOGIN
if not st.session_state.role:
    st.title("🏥 Consultorio Pro SaaS")
    st.caption("Sistema Multi-Consultorio con WhatsApp Integrado")
    tab1, tab2, tab3 = st.tabs(["👨‍⚕️ Doctor", "👩‍💼 Secretaria", "🔐 Super Admin"])

    with tab1:
        user = st.text_input("Usuario Doctor", key="doc_user")
        password = st.text_input("Contraseña", type="password", key="doc_pass")
        if st.button("Entrar", key="doc_btn", type="primary"):
            doctor = asyncio.run(db.doctor.find_unique(where={"username": user}))
            if doctor and check_password(password, doctor.password):
                st.session_state.role = "doctor"
                st.session_state.user_id = doctor.id
                st.rerun()
            else: st.error("Datos incorrectos")

    with tab2:
        user = st.text_input("Usuario Secretaria", key="sec_user")
        password = st.text_input("Contraseña", type="password", key="sec_pass")
        if st.button("Entrar", key="sec_btn", type="primary"):
            sec = asyncio.run(db.secretaria.find_unique(where={"username": user}, include={"doctores": {"include": {"doctor": True}}}))
            if sec and check_password(password, sec.password):
                st.session_state.role = "secretaria"
                st.session_state.user_id = sec.id
                st.session_state.doctores = [d.doctor for d in sec.doctores]
                st.rerun()
            else: st.error("Datos incorrectos")

    with tab3:
        user = st.text_input("Usuario Master", key="admin_user")
        password = st.text_input("Contraseña Master", type="password", key="admin_pass")
        if st.button("Entrar", key="admin_btn", type="primary"):
            if user == st.secrets["SUPER_USER"] and password == st.secrets["SUPER_PASS"]:
                st.session_state.role = "superadmin"
                st.rerun()
            else: st.error("Datos incorrectos")
    st.stop()

# FUNCION PARA GENERAR PDF
def generar_pdf_reporte(doctor, citas, titulo):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header con logo
    c.setFont("Helvetica-Bold", 20)
    c.drawString(1*inch, height - 1*inch, doctor.clinicName)
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, height - 1.3*inch, f"{doctor.doctorName} - {doctor.specialty}")
    c.drawString(1*inch, height - 1.5*inch, titulo)
    c.drawString(1*inch, height - 1.7*inch, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Tabla
    y = height - 2.2*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, y, "Paciente")
    c.drawString(3*inch, y, "Fecha")
    c.drawString(4.5*inch, y, "Status")
    c.drawString(6*inch, y, "Motivo")
    y -= 0.3*inch
    c.setFont("Helvetica", 9)

    for cita in citas:
        if y < 1*inch:
            c.showPage()
            y = height - 1*inch
        c.drawString(1*inch, y, (cita.paciente.nombre or cita.paciente.telefono)[:25])
        c.drawString(3*inch, y, cita.fecha.strftime('%d/%m/%Y %H:%M'))
        c.drawString(4.5*inch, y, cita.status)
        c.drawString(6*inch, y, cita.motivo[:20])
        y -= 0.25*inch

    c.save()
    buffer.seek(0)
    return buffer

# SUPER ADMIN
if st.session_state.role == "superadmin":
    st.title("🔐 Super Admin")
    if st.button("Cerrar Sesión"): st.session_state.clear(); st.rerun()

    tab1, tab2 = st.tabs(["Dar de Alta Doctor", "Asignar Secretarias"])

    with tab1:
        with st.form("alta_doctor", clear_on_submit=True):
            st.subheader("Registrar Nuevo Doctor")
            c1, c2 = st.columns(2)
            clinicName = c1.text_input("Consultorio")
            doctorName = c1.text_input("Doctor")
            specialty = c1.text_input("Especialidad")
            logoUrl = c1.text_input("URL Logo", "https://i.imgur.com/4AiXzf8.png")
            whatsappPhone = c2.text_input("WhatsApp", "526331234567")
            whatsappPhoneId = c2.text_input("WhatsApp Phone ID")
            address = c2.text_input("Dirección")
            horarioLv = c2.text_input("Horario", "09:00-18:00")
            username = st.text_input("Usuario", f"dr{clinicName.lower().replace(' ', '')}")
            password = st.text_input("Contraseña", "cambiar123")
            if st.form_submit_button("Crear Doctor", type="primary"):
                try:
                    doc = asyncio.run(db.doctor.create(data={
                        "clinicName": clinicName, "doctorName": doctorName, "specialty": specialty,
                        "logoUrl": logoUrl, "whatsappPhone": whatsappPhone, "whatsappPhoneId": whatsappPhoneId,
                        "address": address, "horarioLv": horarioLv, "username": username,
                        "password": hash_password(password)
                    }))
                    msg = f"*{clinicName}*\nHola {doctorName}, tu acceso está listo ✅\n\nLink: {st.secrets['APP_URL']}\nUsuario: {username}\nPass: {password}"
                    send_whatsapp(whatsappPhoneId, whatsappPhone, msg)
                    st.success("Doctor creado y notificado por WhatsApp")
                except Exception as e: st.error(f"Error: {e}")

    with tab2:
        st.subheader("Asignar Secretaria a Doctores")
        secretarias = asyncio.run(db.secretaria.find_many())
        doctores = asyncio.run(db.doctor.find_many())
        sec_sel = st.selectbox("Secretaria", secretarias, format_func=lambda x: x.nombre)
        docs_sel = st.multiselect("Doctores que puede manejar", doctores, format_func=lambda x: x.doctorName)
        if st.button("Asignar"):
            for doc in docs_sel:
                asyncio.run(db.doctorsecretaria.create(data={"doctorId": doc.id, "secretariaId": sec_sel.id}))
            st.success("Asignación completada")

# DOCTOR
elif st.session_state.role == "doctor":
    doctor = asyncio.run(db.doctor.find_unique(where={"id": st.session_state.user_id}))
    st.sidebar.image(doctor.logoUrl, use_column_width=True)
    st.sidebar.title(doctor.doctorName)
    st.sidebar.caption(doctor.specialty)
    menu = st.sidebar.radio("Menú", ["📅 Agenda", "🔄 Mover Citas", "👩‍💼 Secretarias", "📊 Reportes"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.clear(); st.rerun()

    if menu == "📅 Agenda":
        st.title("Mi Agenda")
        col1, col2, col3, col4 = st.columns(4)
        hoy = datetime.now().date()
        citas_hoy = asyncio.run(db.cita.count(where={"doctorId": doctor.id, "fecha": {"gte": datetime.combine(hoy, datetime.min.time()), "lt": datetime.combine(hoy, datetime.max.time())}}))
        col1.metric("Citas Hoy", citas_hoy)
        col2.metric("Pendientes", asyncio.run(db.cita.count(where={"doctorId": doctor.id, "status": "PENDIENTE"})))
        col3.metric("Confirmadas", asyncio.run(db.cita.count(where={"doctorId": doctor.id, "status": "CONFIRMADA"})))
        col4.metric("Completadas", asyncio.run(db.cita.count(where={"doctorId": doctor.id, "status": "COMPLETADA"})))

        citas = asyncio.run(db.cita.find_many(where={"doctorId": doctor.id}, include={"paciente": True}, order={"fecha": "asc"}))
        for cita in citas:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3,2,2,2])
                c1.markdown(f"**{cita.paciente.nombre or cita.paciente.telefono}**\n{cita.motivo}")
                c2.write(f"📅 {cita.fecha.strftime('%d/%m/%Y')}\n🕐 {cita.fecha.strftime('%H:%M')}")
                c3.markdown(f"Status: `{cita.status}`")
                if c4.button("✅ Confirmar", key=f"c{cita.id}", disabled=cita.status!="PENDIENTE"):
                    asyncio.run(db.cita.update(where={"id": cita.id}, data={"status": "CONFIRMADA"}))
                    send_whatsapp(doctor.whatsappPhoneId, cita.paciente.telefono, f"*{doctor.clinicName}*\nTu cita fue CONFIRMADA ✅\n{cita.fecha.strftime('%d/%m %H:%M')}")
                    st.rerun()

    elif menu == "🔄 Mover Citas":
        st.title("Mover Cita y Notificar Paciente")
        citas = asyncio.run(db.cita.find_many(where={"doctorId": doctor.id, "status": {"not": "CANCELADA"}}, include={"paciente": True}))
        if citas:
            cita_sel = st.selectbox("Selecciona cita", citas, format_func=lambda x: f"{x.paciente.nombre} - {x.fecha.strftime('%d/%m %H:%M')}")
            c1, c2 = st.columns(2)
            nueva_fecha = c1.date_input("Nueva fecha", cita_sel.fecha.date())
            nueva_hora = c2.time_input("Nueva hora", cita_sel.fecha.time())
            motivo = st.text_area("Motivo del cambio - se enviará al paciente", "Reajuste de agenda")
            if st.button("Mover Cita y Enviar WhatsApp", type="primary"):
                nueva_dt = datetime.combine(nueva_fecha, nueva_hora)
                asyncio.run(db.cita.update(where={"id": cita_sel.id}, data={"fecha": nueva_dt}))
                msg = f"*{doctor.clinicName}*\nHola {cita_sel.paciente.nombre}, tu cita fue REAGENDADA por indicación del {doctor.doctorName}.\n\n📅 Nueva fecha: *{nueva_dt.strftime('%d/%m/%Y %H:%M')}*\n\nMotivo: {motivo}\n\nLamentamos el inconveniente."
                send_whatsapp(doctor.whatsappPhoneId, cita_sel.paciente.telefono, msg)
                st.success("Cita movida y paciente notificado")

    elif menu == "👩‍💼 Secretarias":
        st.title("Gestionar Secretarias")
        with st.form("nueva_sec"):
            nombre = st.text_input("Nombre completo")
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña")
            if st.form_submit_button("Crear Secretaria"):
                sec = asyncio.run(db.secretaria.create(data={"nombre": nombre, "username": username, "password": hash_password(password)}))
                asyncio.run(db.doctorsecretaria.create(data={"doctorId": doctor.id, "secretariaId": sec.id}))
                st.success(f"Secretaria {nombre} creada con acceso a tu agenda")

    elif menu == "📊 Reportes":
        st.title("Reportes y Estadísticas")
        tab1, tab2, tab3 = st.tabs(["Semanal", "Mensual", "Rango Personalizado"])

        def mostrar_reporte(inicio, fin, titulo):
            citas = asyncio.run(db.cita.find_many(where={"doctorId": doctor.id, "fecha": {"gte": inicio, "lte": fin}}, include={"paciente": True}))
            df = pd.DataFrame([{"Paciente": c.paciente.nombre, "Fecha": c.fecha, "Status": c.status, "Motivo": c.motivo} for c in citas])
            if df.empty: st.info("No hay citas en este período"); return

            col1, col2 = st.columns(2)
            fig1 = px.pie(df, names="Status", title="Distribución por Status")
            col1.plotly_chart(fig1, use_container_width=True)
            fig2 = px.bar(df.groupby(df["Fecha"].dt.date).size().reset_index(name="Citas"), x="Fecha", y="Citas", title="Citas por Día")
            col2.plotly_chart(fig2, use_container_width=True)

            st.dataframe(df, use_container_width=True)
            pdf = generar_pdf_reporte(doctor, citas, titulo)
            st.download_button("📥 Descargar PDF", pdf, f"reporte_{doctor.username}_{titulo}.pdf", "application/pdf")

        with tab1:
            hoy = datetime.now()
            inicio_sem = hoy - timedelta(days=hoy.weekday())
            mostrar_reporte(inicio_sem, inicio_sem + timedelta(days=6), "Reporte Semanal")
        with tab2:
            hoy = datetime.now()
            inicio_mes = hoy.replace(day=1)
            mostrar_reporte(inicio_mes, hoy, "Reporte Mensual")
        with tab3:
            c1, c2 = st.columns(2)
            inicio = c1.date_input("Desde", date.today() - timedelta(days=30))
            fin = c2.date_input("Hasta", date.today())
            if st.button("Generar Reporte"): mostrar_reporte(datetime.combine(inicio, datetime.min.time()), datetime.combine(fin, datetime.max.time()), f"Reporte {inicio} a {fin}")

# SECRETARIA MULTI-DOCTOR
elif st.session_state.role == "secretaria":
    sec = asyncio.run(db.secretaria.find_unique(where={"id": st.session_state.user_id}))
    st.sidebar.title(f"👩‍💼 {sec.nombre}")
    if st.sidebar.button("Cerrar Sesión"): st.session_state.clear(); st.rerun()

    # Selector de doctor
    doctores = st.session_state.doctores
    if not doctores: st.error("No tienes doctores asignados"); st.stop()

    doc_sel = st.sidebar.selectbox("Trabajando en agenda de:", doctores, format_func=lambda x: x.doctorName)
    st.sidebar.image(doc_sel.logoUrl, width=100)
    st.title(f"Agenda de {doc_sel.doctorName}")

    tab1, tab2 = st.tabs(["Agendar Cita", "Ver Agenda del Día"])

    with tab1:
        telefono = st.text_input("Teléfono paciente")
        nombre = st.text_input("Nombre paciente")
        c1, c2 = st.columns(2)
        fecha = c1.date_input("Fecha")
        hora = c2.time_input("Hora")
        motivo = st.text_input("Motivo", "Consulta general")
        if st.button("Agendar y Notificar", type="primary"):
            paciente = asyncio.run(db.paciente.find_unique(where={'telefono_doctorId': {'telefono': telefono, 'doctorId': doc_sel.id}}))
            if not paciente:
                paciente = asyncio.run(db.paciente.create(data={'telefono': telefono, 'nombre': nombre, 'doctorId': doc_sel.id}))
            asyncio.run(db.cita.create(data={'pacienteId': paciente.id, 'doctorId': doc_sel.id, 'fecha': datetime.combine(fecha, hora), 'motivo': motivo, 'creadaPor': 'SECRETARIA', 'status': 'CONFIRMADA'}))
            send_whatsapp(doc_sel.whatsappPhoneId, telefono, f"*{doc_sel.clinicName}*\nHola {nombre}, tu cita quedó confirmada para el {fecha.strftime('%d/%m/%Y')} {hora}")
            st.success("Cita agendada")

    with tab2:
        hoy = datetime.now().date()
        citas_hoy = asyncio.run(db.cita.find_many(where={"doctorId": doc_sel.id, "fecha": {"gte": datetime.combine(hoy, datetime.min.time()), "lt": datetime.combine(hoy, datetime.max.time())}}, include={"paciente": True}))
        for cita in citas_hoy:
            st.write(f"**{cita.fecha.strftime('%H:%M')}** - {cita.paciente.nombre} - {cita.status}")
