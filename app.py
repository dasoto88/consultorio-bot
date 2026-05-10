from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prisma import Prisma
from pydantic import BaseModel
from typing import Optional
import os

# Inicializar FastAPI
app = FastAPI(title="Consultorio Bot API")

# CORS para que puedas probar desde otros dominios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar cliente de Prisma
db = Prisma()

# Modelos Pydantic para requests
class DoctorCreate(BaseModel):
    nombre: str
    especialidad: Optional[str] = None
    email: Optional[str] = None

class PacienteCreate(BaseModel):
    nombre: str
    telefono: Optional[str] = None
    doctorId: int

# Eventos de inicio y cierre
@app.on_event("startup")
async def startup():
    await db.connect()
    print("Conectado a la base de datos")

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()
    print("Desconectado de la base de datos")

# Rutas
@app.get("/")
async def root():
    return {"status": "ok", "message": "Consultorio Bot API funcionando"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Doctores
@app.get("/doctores")
async def get_doctores():
    doctores = await db.doctor.find_many()
    return doctores

@app.post("/doctores")
async def create_doctor(doctor: DoctorCreate):
    nuevo_doctor = await db.doctor.create(data=doctor.model_dump())
    return nuevo_doctor

# Pacientes
@app.get("/pacientes")
async def get_pacientes():
    pacientes = await db.paciente.find_many()
    return pacientes

@app.post("/pacientes")
async def create_paciente(paciente: PacienteCreate):
    nuevo_paciente = await db.paciente.create(data=paciente.model_dump())
    return nuevo_paciente

@app.get("/pacientes/{paciente_id}")
async def get_paciente(paciente_id: int):
    paciente = await db.paciente.find_unique(where={"id": paciente_id})
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return paciente
