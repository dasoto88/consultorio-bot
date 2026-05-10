import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import httpx

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    name = Column(String)
    role = Column(String, default="DOCTOR")

class Patient(Base):
    __tablename__ = "Patient"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String, unique=True, index=True)
    email = Column(String, nullable=True)
    birthDate = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    doctorId = Column(Integer)

class Appointment(Base):
    __tablename__ = "Appointment"
    id = Column(Integer, primary_key=True, index=True)
    patientId = Column(Integer)
    doctorId = Column(Integer)
    date = Column(DateTime)
    reason = Column(String, nullable=True)
    status = Column(String, default="SCHEDULED")
    notes = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not pwd_context.verify(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token({"sub": user.email, "id": user.id, "role": user.role})
    return {"access_token": token, "user": {"id": user.id, "name": user.name, "role": user.role}}

@app.get("/patients")
def get_patients(user=Depends(verify_token), db: Session = Depends(get_db)):
    patients = db.query(Patient).filter(Patient.doctorId == user["id"]).all()
    return patients

@app.get("/appointments")
def get_appointments(user=Depends(verify_token), db: Session = Depends(get_db)):
    appointments = db.query(Appointment).filter(Appointment.doctorId == user["id"]).all()
    return appointments

@app.get("/")
def root():
    return {"status": "ok"}
