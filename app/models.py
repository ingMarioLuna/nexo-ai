from app.database import Base
from sqlalchemy import Column, Integer, String, Text

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    original_message = Column(Text, nullable=False)
    categoria = Column(String, nullable=True)
    prioridad = Column(String, nullable=True)
    departamento_responsable = Column(String, nullable=True)
    diagnostico_breve = Column(Text, nullable=True)
    solucion_sugerida = Column(Text, nullable=True)
    source = Column(String, default="Ollama (Local AI)")
    