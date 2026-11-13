from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RequestLog
from app.services.ai_service import classify_and_solve_issue
from pydantic import BaseModel
import io
import httpx
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import decode_access_token

# Importaciones para Excel profesional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

router = APIRouter()
security = HTTPBearer()

class RequestInput(BaseModel):
    message: str
    model: Optional[str] = "llama3.2"

@router.post("/classify-ai")
def classify_request_ai(request: RequestInput, db: Session = Depends(get_db)):
    # Pasamos tanto el mensaje como el modelo seleccionado por el usuario en la interfaz
    ai_analysis = classify_and_solve_issue(message=request.message, model=request.model or "llama3.2")

    if "error" in ai_analysis:
        return ai_analysis

    db_log = RequestLog(
        original_message=request.message,
        categoria=ai_analysis.get("categoria", "Personal"),
        prioridad=ai_analysis.get("prioridad", "Baja"),
        departamento_responsable=ai_analysis.get("departamento_responsable", "General"),
        diagnostico_breve=ai_analysis.get("diagnostico_breve", "Procesado correctamente"),
        solucion_sugerida=ai_analysis.get("solucion_sugerida", "Sin solución"),
        source="Ollama (Local AI)"
    )

    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    return {
        "id_registro": db_log.id,
        "original_message": request.message,
        "categoria": db_log.categoria,
        "diagnostico_breve": db_log.diagnostico_breve,
        "prioridad": db_log.prioridad,
        "departamento_responsable": db_log.departamento_responsable,
        "solucion_sugerida": db_log.solucion_sugerida,
        "source": "Ollama (Local AI)"
    }

# ENDPOINT DE HISTORIAL CON FILTROS OPCIONALES
@router.get("/history")
def get_request_history(
    prioridad: Optional[str] = None,
    departamento: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(RequestLog)

    if prioridad:
        query = query.filter(RequestLog.prioridad.ilike(f"%{prioridad}%"))
    if departamento:
        query = query.filter(RequestLog.departamento_responsable.ilike(f"%{departamento}%"))

    logs = query.all()
    
    return {
        "total_registros": len(logs),
        "filtros_aplicados": {
            "prioridad": prioridad,
            "departamento": departamento
        },
        "historial": [
            {
                "id": log.id,
                "original_message": log.original_message,
                "categoria": log.categoria,
                "prioridad": log.prioridad,
                "departamento_responsable": log.departamento_responsable,
                "diagnostico_breve": log.diagnostico_breve,
                "solucion_sugerida": log.solucion_sugerida,
                "source": log.source
            }
            for log in logs
        ]
    }

# ENDPOINT: Exportar historial a Excel estilizado (Protegido solo para Admin)
@router.get("/export/excel")
def export_requests_excel(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token inválido o expirado"
        )
    
    username = payload.get("sub")
    if username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acceso denegado: Solo el administrador puede exportar reportes."
        )

    logs = db.query(RequestLog).all()
    
    # Crear libro de Excel profesional con openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte NEXO AI"

    # Mostrar líneas de cuadrícula explícitamente
    ws.views.sheetView[0].showGridLines = True

    # Cabeceras
    headers = ["ID", "Mensaje Original", "Categoría", "Prioridad", "Departamento", "Diagnóstico", "Solución", "Fuente"]
    ws.append(headers)
    
    # Escribir filas de datos
    for log in logs:
        ws.append([
            log.id,
            log.original_message,
            log.categoria,
            log.prioridad,
            log.departamento_responsable,
            log.diagnostico_breve,
            log.solucion_sugerida,
            log.source
        ])
        
    # Estilos profesionales (Paleta Corporativa)
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    zebra_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    cell_font = Font(name="Segoe UI", size=10)

    thin_border = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    # Aplicar estilos y bordes a celdas
    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=len(logs) + 1, min_col=1, max_col=8), start=1):
        for cell in row:
            cell.border = thin_border
            if row_idx == 1:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            else:
                cell.font = cell_font
                if row_idx % 2 == 0:
                    cell.fill = zebra_fill
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # Convertir en Tabla oficial de Excel con filtros automáticos superiores
    if len(logs) > 0:
        tab = Table(displayName="TablaNexoAIReporte", ref=f"A1:H{len(logs) + 1}")
        style = TableStyleInfo(name="TableStyleLight9", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
        tab.tableStyleInfo = style
        ws.add_table(tab)

    # Auto-ajustar ancho de columnas de forma inteligente
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 15), 45)

    # Guardar en memoria virtual para descarga directa por streaming
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=nexo_ai_reporte.xlsx"}
    )

# ENDPOINT: Listar modelos disponibles en Ollama
@router.get("/models")
def get_ollama_models():
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            return {"models": models if models else ["llama3.2"]}
        return {"models": ["llama3.2"]}
    except Exception as e:
        return {"models": ["llama3.2"]}