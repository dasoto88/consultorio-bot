import streamlit as st
import asyncio
import os
from prisma import Prisma
from datetime import datetime

st.set_page_config(page_title="Admin Consultorio", layout="wide", page_icon="🏥")

@st.cache_resource
def init_db():
    db = Prisma()
    asyncio.run(db.connect())
    return db

db = init_db()

# LOGIN
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso - Panel Médico")
    st.subheader(st.secrets.get("CLINIC_NAME", "Consultorio"))
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar", type="primary"):
        if user == st.secrets["ADMIN_USER"] and password == st.secrets["ADMIN_PASSWORD"]:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop()

# PANEL PRINCIPAL
col1, col2, col3 = st.columns([1, 5, 1])
with col1:
    st.image(st.secrets["LOGO_URL"], width=80)
with col2:
    st.title(st.secrets["CLINIC_NAME"])
    st.caption(f"{st.secrets['DOCTOR_NAME']} | {st.secrets['DOCTOR_SPECIALTY']} | {st.secrets['PHONE_NUMBER']}")
with col3:
    if st.button("Cerrar Sesión"): st.session_state.clear(); st.rerun()

st.divider()

# MÉTRICAS RÁPIDAS
citas = asyncio.run(db.cita.find_many(include={'paciente': True}, order={'fecha': 'asc'}))
pendientes = len([c for c in citas if c.status == "PENDIENTE"])
confirmadas = len([c for c in citas if c.status == "CONFIRMADA"])

k1, k2, k3 = st.columns(3)
k1.metric("Citas Pendientes", pendientes)
k2.metric("Citas Confirmadas", confirmadas)
k3.metric("Total Pacientes", len(set([c.pacienteId for c in citas])))

st.header("📅 Agenda de Citas")

if not citas:
    st.info("Aún no hay citas agendadas. Los pacientes pueden agendar por WhatsApp.")
else:
    for cita in citas:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([2.5, 2, 2, 1.5, 2])
            c1.markdown(f"**{cita.paciente.nombre or 'Nombre pendiente'}**")
            c2.write(f"📱 {cita.paciente.telefono}")
            c3.write(f"🗓️ {cita.fecha.strftime('%d/%m/%Y %H:%M')}")

            status_color = {"PENDIENTE": "orange", "CONFIRMADA": "green", "CANCELADA": "red"}
            c4.markdown(f":{status_color[cita.status]}[**{cita.status}**]")

            with c5:
                if cita.status == "PENDIENTE":
                    if st.button("✅ Confirmar", key=f"conf_{cita.id}", use_container_width=True):
                        asyncio.run(db.cita.update(where={'id': cita.id}, data={'status': 'CONFIRMADA'}))
                        st.toast("Cita confirmada")
                        st.rerun()
                if cita.status!= "CANCELADA":
                    if st.button("❌ Cancelar", key=f"canc_{cita.id}", use_container_width=True):
                        asyncio.run(db.cita.update(where={'id': cita.id}, data={'status': 'CANCELADA'}))
                        st.toast("Cita cancelada")
                        st.rerun()