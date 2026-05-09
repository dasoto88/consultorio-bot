import os
import requests
from fastapi import FastAPI, Request
from prisma import Prisma
from datetime import datetime

app = FastAPI()
db = Prisma()

@app.on_event("startup")
async def startup(): await db.connect()

def send_whatsapp(phone_id, to, text):
    requests.post(f"https://graph.facebook.com/v20.0/{phone_id}/messages",
        headers={"Authorization": f"Bearer {os.getenv('MASTER_WHATSAPP_TOKEN')}"},
        json={"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
    )

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    try:
        value = data['entry'][0]['changes'][0]['value']
        phone_id = value['metadata']['phone_number_id']
        msg = value['messages'][0]
        from_num = msg['from']
        text = msg.get('text', {}).get('body', '').strip()
    except: return {"status": "ok"}

    doctor = await db.doctor.find_unique(where={"whatsappPhoneId": phone_id})
    if not doctor: return {"status": "no doctor"}

    paciente = await db.paciente.find_unique(where={'telefono_doctorId': {'telefono': from_num, 'doctorId': doctor.id}})
    if not paciente:
        paciente = await db.paciente.create(data={'telefono': from_num, 'doctorId': doctor.id})

    if 'cita' in text.lower():
        respuesta = f"*{doctor.clinicName}*\nHola, soy el asistente de {doctor.doctorName}.\nPara agendar escribe fecha: *DD/MM*"
    elif "/" in text and text.replace('/','').isdigit():
        dia, mes = map(int, text.split('/'))
        año = datetime.now().year if mes >= datetime.now().month else datetime.now().year + 1
        fecha = datetime(año, mes, dia, 10, 0)
        await db.cita.create(data={'pacienteId': paciente.id, 'doctorId': doctor.id, 'fecha': fecha})
        respuesta = f"Pre-agendé tu cita para {text} 10:00am. Escribe tu *nombre completo* para confirmar."
    elif not paciente.nombre:
        await db.paciente.update(where={'id': paciente.id}, data={'nombre': text})
        respuesta = f"Gracias {text}. Tu cita está pendiente. El doctor te confirma en breve."
    else:
        respuesta = f"Hola {paciente.nombre}. Escribe *cita* para agendar."

    send_whatsapp(doctor.whatsappPhoneId, from_num, respuesta)
    return {"status": "ok"}

@app.get("/webhook")
async def verify(request: Request):
    if request.query_params.get('hub.verify_token') == os.getenv('VERIFY_TOKEN'):
        return int(request.query_params.get('hub.challenge'))
