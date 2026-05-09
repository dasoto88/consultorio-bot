import os
import requests
from fastapi import FastAPI, Request
from prisma import Prisma
from datetime import datetime, timedelta

app = FastAPI()
db = Prisma()

@app.on_event("startup")
async def startup(): await db.connect()

def send_whatsapp(to, text):
    url = f"https://graph.facebook.com/v20.0/{os.getenv('WHATSAPP_PHONE_ID')}/messages"
    headers = {"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"}
    data = {"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
    requests.post(url, headers=headers, json=data)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    try:
        msg = data['entry'][0]['changes'][0]['value']['messages'][0]
        from_num = msg['from']
        text = msg.get('text', {}).get('body', '').strip()
    except:
        return {"status": "ok"}

    paciente = await db.paciente.find_unique(where={'telefono': from_num})
    if not paciente:
        paciente = await db.paciente.create(data={'telefono': from_num})

    CLINIC = os.getenv('CLINIC_NAME')
    DOCTOR = os.getenv('DOCTOR_NAME')
    respuesta = ""

    if 'cita' in text.lower() or 'hola' in text.lower():
        respuesta = f"*{CLINIC}*\nHola, soy el asistente de {DOCTOR} 👨‍⚕️\n\nPara agendar escribe la fecha: *DD/MM* Ej: 15/05\nHorario: {os.getenv('HORARIO_LV')}"

    elif "/" in text and text.replace('/', '').isdigit():
        dia, mes = map(int, text.split('/'))
        año = datetime.now().year if mes >= datetime.now().month else datetime.now().year + 1
        fecha = datetime(año, mes, dia, 10, 0)
        await db.cita.create(data={'pacienteId': paciente.id, 'fecha': fecha, 'status': 'PENDIENTE'})
        respuesta = f"Fecha *{text}* pre-agendada a las 10:00am.\n\nPara confirmar escribe tu *nombre completo*."

    elif not paciente.nombre and len(text) > 3:
        await db.paciente.update(where={'id': paciente.id}, data={'nombre': text})
        respuesta = f"Gracias {text}. Tu cita quedó *PENDIENTE DE CONFIRMACIÓN*.\nTe avisamos por aquí cuando el doctor la confirme."

    else:
        respuesta = f"Hola {paciente.nombre or ''}. Escribe *cita* para agendar.\nUbicación: {os.getenv('ADDRESS')}"

    send_whatsapp(from_num, respuesta)
    return {"status": "ok"}

@app.get("/webhook")
async def verify(request: Request):
    if request.query_params.get('hub.verify_token') == os.getenv('VERIFY_TOKEN'):
        return int(request.query_params.get('hub.challenge'))
