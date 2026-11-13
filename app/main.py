from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine, SessionLocal
from app.models import User
from app.services.auth_service import hash_password
from app.api.routes import router as ai_requests_router
from app.api.auth_routes import router as auth_router

# 1. Crear las tablas en SQLite si no existen
Base.metadata.create_all(bind=engine)

# 2. Única instancia principal de FastAPI
app = FastAPI(
    title="NEXO AI",
    description="Intelligent Business Operations Copilot with Local AI",
    version="2.0",
)

# 3. Crear usuario administrador por defecto al iniciar la app
@app.on_event("startup")
def create_default_admin():
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            hashed_pwd = hash_password("admin123")
            new_user = User(username="admin", hashed_password=hashed_pwd)
            db.add(new_user)
            db.commit()
            print(">>> Usuario administrador por defecto creado: admin / admin123")
    finally:
        db.close()

# 4. Endpoint de salud / estado del backend
@app.get("/health")
def health_check():
    return {
        "application": "NEXO AI",
        "message": "Welcome to NEXO AI - Backend Running with SQLite",
        "status": "running",
    }

# 5. Incluir todos los routers de la API
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(ai_requests_router, prefix="/api/v1/requests", tags=["AI Requests"])

# 6. Montar la carpeta 'static' en la ruta raíz para servir el panel visual
app.mount("/", StaticFiles(directory="static", html=True), name="static")