from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prisma import Prisma
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import httpx
import os
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import AsyncOpenAI

app = FastAPI(title="ConsultorioBot API")
db = Prisma()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
scheduler = AsyncIOScheduler()

# CORS para que React pueda hablar con la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CONFIG
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esta-key-por-algo-seguro-123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "consultoriobot123")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") # Pega tu key de OpenAI aquí o en Render

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# MODELOS
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class DoctorCreate(BaseModel):
    name: str
    email: str
    password: str
    cedula: str
    especialidad: str
    whatsappNumber: str
    whatsappPhoneId: str
    accessToken: str
    horarioInicio: str = "09:00"
    horarioFin: str = "18:00"
    duracionCita: int = 30

class SecretaryCreate(BaseModel):
    name: str
    email: str
    password: str
    doctorIds: list[str] # IDs de doctores a asignar

class AppointmentCreate(BaseModel):
    patientName: str
    patientPhone: str
    fecha: str
    motivo: str

# STARTUP
@app.on_event("startup")
async def startup():
    await db.connect()
    # Crear super admin
    admin = await db.user.find_unique(where={"email": "admin@consultoriobot.com"})
    if not admin:
        hashed = pwd_context.hash("admindasoto88")
        await db.user.create(
            data={
                "email": "admin@consultoriobot.com",
                "password": hashed,
                "name": "Super Admin",
                "role": "SUPER_ADMIN"
            }
        )
    # Iniciar cron de recordatorios
    scheduler.add_job(check_reminders, "interval", minutes=5)
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    await db.disconnect()

# HELPERS
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = await db.user.find_unique(where={"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user

async def send_whatsapp_message(phone_number_id: str, access_token: str, to: str, message: str):
    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=data)

# IA: Extraer fecha/hora de texto natural
async def parse_appointment_with_ai(text: str, doctor_hours: dict):
    if not openai_client:
        # Fallback simple sin OpenAI
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', text)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month}-{day}T10:00:00"
        return None

    prompt = f"""
    Eres un asistente que extrae fechas y horas de citas médicas.
    Horario del doctor: {doctor_hours['inicio']} a {doctor_hours['fin']}.
    Hoy es: {datetime.now().strftime('%Y-%m-%d %H:%M')}.

    Texto del paciente: "{text}"

    Responde SOLO con fecha y hora en formato ISO 8601: YYYY-MM-DDTHH:MM:SS
    Si no hay fecha clara, responde: null
    """
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result = response.choices[0].message.content.strip()
        return result if result!= "null" else None
    except:
        return None

# CRON: Enviar recordatorios
async def check_reminders():
    now = datetime.now()
    reminders = await db.reminder.find_many(
        where={"sent": False, "sendAt": {"lte": now}},
        include={"appointment": {"include": {"patient": True, "doctor": {"include": {"user": True}}}}}
    )
    for rem in reminders:
        appt = rem.appointment
        msg = f"⏰ Recordatorio: Tienes cita con Dr. {appt.doctor.user.name}\n📅 {appt.fecha.strftime('%d/%m/%Y a las %H:%M')}\n📍 Motivo: {appt.motivo}"
        await send_whatsapp_message(
            appt.doctor.whatsappPhoneId,
            appt.doctor.accessToken,
            appt.patient.phone,
            msg
        )
        await db.reminder.update(where={"id": rem.id}, data={"sent": True})

# RUTAS
@app.get("/", response_class=HTMLResponse)
def serve_admin_panel():
    # Sirve el React compilado
    return FileResponse("static/index.html")

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.user.find_unique(where={"email": form_data.username})
    if not user or not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Email o password incorrecto")
    token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role}

# WEBHOOK WHATSAPP CON IA
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403)

@app.post("/webhook")
async def receive_whatsapp(request: Request):
    data = await request.json()
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" not in entry:
            return {"status": "ok"}
        message = entry["messages"][0]
        from_number = message["from"]
        phone_number_id = entry["metadata"]["phone_number_id"]
        text = message["text"]["body"]

        doctor = await db.doctor.find_unique(where={"whatsappPhoneId": phone_number_id}, include={"user": True})
        if not doctor:
            return {"status": "ok"}

        # IA para entender intención
        fecha_iso = await parse_appointment_with_ai(text, {
            "inicio": doctor.horarioInicio,
            "fin": doctor.horarioFin
        })

        if fecha_iso:
            fecha_dt = date_parser.parse(fecha_iso)
            # VALIDAR CHOQUE DE HORARIOS
            fin_cita = fecha_dt + timedelta(minutes=doctor.duracionCita)
            choque = await db.appointment.find_first(
                where={
                    "doctorId": doctor.id,
                    "status": {"in": ["PENDIENTE", "CONFIRMADA"]},
                    "OR": [
                        {"fecha": {"gte": fecha_dt, "lt": fin_cita}},
                        {"fecha": {"lte": fecha_dt}}
                    ]
                }
            )
            if choque:
                await send_whatsapp_message(
                    phone_number_id, doctor.accessToken, from_number,
                    f"Lo siento, ese horario ya está ocupado. Horarios disponibles: {doctor.horarioInicio} - {doctor.horarioFin}"
                )
                return {"status": "conflict"}

            # Crear paciente si no existe
            patient = await db.patient.find_unique(
                where={"doctorId_phone": {"doctorId": doctor.id, "phone": from_number}}
            )
            if not patient:
                patient = await db.patient.create(
                    data={"doctorId": doctor.id, "name": "Paciente WhatsApp", "phone": from_number}
                )

            # Crear cita
            appt = await db.appointment.create(
                data={
                    "doctorId": doctor.id,
                    "patientId": patient.id,
                    "createdById": doctor.userId,
                    "fecha": fecha_dt,
                    "motivo": "Cita por WhatsApp",
                    "status": "CONFIRMADA",
                    "origen": "WHATSAPP"
                }
            )
            # Crear recordatorio 24h antes
            await db.reminder.create(
                data={
                    "appointmentId": appt.id,
                    "sendAt": fecha_dt - timedelta(hours=24)
                }
            )
            await send_whatsapp_message(
                phone_number_id, doctor.accessToken, from_number,
                f"✅ Cita confirmada para el {fecha_dt.strftime('%d/%m/%Y a las %H:%M')} con Dr. {doctor.user.name}"
            )
        else:
            await send_whatsapp_message(
                phone_number_id, doctor.accessToken, from_number,
                f"Hola, soy el asistente del Dr. {doctor.user.name}. Dime qué día y hora quieres tu cita. Ej: 'Mañana a las 3pm'"
            )
        return {"status": "ok"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error"}

# ADMIN ROUTES
@app.post("/admin/doctors")
async def create_doctor(doc: DoctorCreate, user = Depends(get_current_user)):
    if user.role!= "SUPER_ADMIN":
        raise HTTPException(403)
    hashed = pwd_context.hash(doc.password)
    new_user = await db.user.create(
        data={"email": doc.email, "password": hashed, "name": doc.name, "role": "DOCTOR"}
    )
    new_doc = await db.doctor.create(
        data={
            "userId": new_user.id,
            "cedula": doc.cedula,
            "especialidad": doc.especialidad,
            "whatsappNumber": doc.whatsappNumber,
            "whatsappPhoneId": doc.whatsappPhoneId,
            "accessToken": doc.accessToken,
            "horarioInicio": doc.horarioInicio,
            "horarioFin": doc.horarioFin,
            "duracionCita": doc.duracionCita
        }
    )
    return new_doc

@app.get("/admin/doctors")
async def list_doctors(user = Depends(get_current_user)):
    if user.role!= "SUPER_ADMIN":
        raise HTTPException(403)
    return await db.doctor.find_many(include={"user": True})

@app.post("/admin/secretaries")
async def create_secretary(sec: SecretaryCreate, user = Depends(get_current_user)):
    if user.role!= "SUPER_ADMIN":
        raise HTTPException(403)
    hashed = pwd_context.hash(sec.password)
    new_user = await db.user.create(
        data={"email": sec.email, "password": hashed, "name": sec.name, "role": "SECRETARY"}
    )
    new_sec = await db.secretary.create(data={"userId": new_user.id})
    for doc_id in sec.doctorIds:
        await db.secretarydoctor.create(data={"secretaryId": new_sec.id, "doctorId": doc_id})
    return new_sec

# DOCTOR/SECRETARY ROUTES
@app.get("/api/appointments")
async def get_appointments(user = Depends(get_current_user)):
    if user.role == "DOCTOR":
        doc = await db.doctor.find_unique(where={"userId": user.id})
        return await db.appointment.find_many(
            where={"doctorId": doc.id},
            include={"patient": True},
            order={"fecha": "asc"}
        )
    elif user.role == "SECRETARY":
        sec = await db.secretary.find_unique(
            where={"userId": user.id},
            include={"doctors": True}
        )
        doc_ids = [sd.doctorId for sd in sec.doctors]
        return await db.appointment.find_many(
            where={"doctorId": {"in": doc_ids}},
            include={"patient": True, "doctor": {"include": {"user": True}}},
            order={"fecha": "asc"}
        )
    raise HTTPException(403)

@app.post("/api/appointments")
async def create_appointment(appt: AppointmentCreate, user = Depends(get_current_user)):
    if user.role == "DOCTOR":
        doctor = await db.doctor.find_unique(where={"userId": user.id}, include={"user": True})
    else:
        sec = await db.secretary.find_unique(where={"userId": user.id}, include={"doctors": {"include": {"doctor": {"include": {"user": True}}}}})
        doctor = sec.doctors[0].doctor

    fecha_dt = date_parser.parse(appt.fecha)
    fin_cita = fecha_dt + timedelta(minutes=doctor.duracionCita)

    # Validar choque
    choque = await db.appointment.find_first(
        where={
            "doctorId": doctor.id,
            "status": {"in": ["PENDIENTE", "CONFIRMADA"]},
            "fecha": {"lt": fin_cita, "gte": fecha_dt}
        }
    )
    if choque:
        raise HTTPException(400, detail="Horario ocupado")

    patient = await db.patient.find_unique(
        where={"doctorId_phone": {"doctorId": doctor.id, "phone": appt.patientPhone}}
    )
    if not patient:
        patient = await db.patient.create(
            data={"doctorId": doctor.id, "name": appt.patientName, "phone": appt.patientPhone}
        )

    new_appt = await db.appointment.create(
        data={
            "doctorId": doctor.id,
            "patientId": patient.id,
            "createdById": user.id,
            "fecha": fecha_dt,
            "motivo": appt.motivo,
            "status": "CONFIRMADA"
        }
    )
    await db.reminder.create(
        data={"appointmentId": new_appt.id, "sendAt": fecha_dt - timedelta(hours=24)}
    )
    await send_whatsapp_message(
        doctor.whatsappPhoneId, doctor.accessToken, appt.patientPhone,
        f"✅ Cita confirmada con Dr. {doctor.user.name}\n📅 {fecha_dt.strftime('%d/%m/%Y a las %H:%M')}"
    )
    return new_appt

@app.put("/api/appointments/{aid}")
async def update_appointment(aid: str, data: dict, user = Depends(get_current_user)):
    appt = await db.appointment.find_unique(
        where={"id": aid},
        include={"doctor": {"include": {"user": True}}, "patient": True}
    )
    if not appt:
        raise HTTPException(404)

    if "fecha" in data:
        nueva_fecha = date_parser.parse(data["fecha"])
        fin = nueva_fecha + timedelta(minutes=appt.doctor.duracionCita)
        choque = await db.appointment.find_first(
            where={
                "id": {"not": aid},
                "doctorId": appt.doctorId,
                "fecha": {"lt": fin, "gte": nueva_fecha}
            }
        )
        if choque:
            raise HTTPException(400, "Nuevo horario ocupado")

    updated = await db.appointment.update(where={"id": aid}, data=data)

    msg = f"📢 Tu cita con Dr. {appt.doctor.user.name} fue actualizada.\n"
    if "fecha" in data:
        msg += f"📅 Nueva fecha: {nueva_fecha.strftime('%d/%m/%Y a las %H:%M')}\n"
    if data.get("status") == "CANCELADA":
        msg += "❌ Cita cancelada."

    await send_whatsapp_message(appt.doctor.whatsappPhoneId, appt.doctor.accessToken, appt.patient.phone, msg)
    return updated
