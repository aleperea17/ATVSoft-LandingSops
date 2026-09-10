import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr

from .database import get_connection, init_db

app = FastAPI(title="SOPs Landing")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Clave del panel. Se puede pisar con la variable de entorno DASHBOARD_PASSWORD
# sin tocar el código ni volver a buildear.
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "atv500k")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class LeadIn(BaseModel):
    slug: str = ""
    nombre: str
    telefono: str
    email: EmailStr
    instagram: str
    atrae_clientes: str
    perfil: str
    cuello_botella: str = ""


class LeadOut(BaseModel):
    id: int


@app.post("/api/leads", response_model=LeadOut)
def create_lead(lead: LeadIn) -> LeadOut:
    nombre = lead.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío.")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO leads
                (slug, nombre, telefono, email, instagram, atrae_clientes, perfil, cuello_botella)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead.slug.strip(),
                nombre,
                lead.telefono.strip(),
                lead.email.lower().strip(),
                lead.instagram.strip(),
                lead.atrae_clientes.strip(),
                lead.perfil.strip(),
                lead.cuello_botella.strip(),
            ),
        )
        conn.commit()
        return LeadOut(id=cur.lastrowid)


class CodeIn(BaseModel):
    code: str
    lead_id: Optional[int] = None


class CodeOut(BaseModel):
    valid: bool


@app.post("/api/validate-code", response_model=CodeOut)
def validate_code(payload: CodeIn) -> CodeOut:
    normalized = payload.code.strip().upper()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM codes WHERE code = ? AND active = 1", (normalized,)
        ).fetchone()
        if row is None:
            return CodeOut(valid=False)
        # Sin lead_id: solo verifica (paso inicial). Con lead_id: registra el uso.
        if payload.lead_id is not None:
            conn.execute(
                "UPDATE codes SET times_used = times_used + 1 WHERE id = ?", (row["id"],)
            )
            conn.execute(
                "UPDATE leads SET codigo_usado = ? WHERE id = ?",
                (normalized, payload.lead_id),
            )
            conn.commit()
        return CodeOut(valid=True)


def _check_dashboard_key(key: Optional[str]) -> None:
    if key != DASHBOARD_PASSWORD:
        raise HTTPException(status_code=401, detail="Clave de acceso inválida.")


@app.get("/api/dashboard/summary")
def dashboard_summary(key: str = Query(...)):
    _check_dashboard_key(key)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                COALESCE(NULLIF(slug, ''), '(sin slug)') AS slug,
                COUNT(*) AS total,
                SUM(CASE WHEN codigo_usado IS NOT NULL THEN 1 ELSE 0 END) AS con_clave
            FROM leads
            GROUP BY slug
            ORDER BY total DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/dashboard/leads")
def dashboard_leads(key: str = Query(...), slug: Optional[str] = None):
    _check_dashboard_key(key)
    with get_connection() as conn:
        if slug and slug != "(sin slug)":
            rows = conn.execute(
                "SELECT * FROM leads WHERE slug = ? ORDER BY created_at DESC",
                (slug,),
            ).fetchall()
        elif slug == "(sin slug)":
            rows = conn.execute(
                "SELECT * FROM leads WHERE slug = '' ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leads ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]


# Estados del seguimiento. El vacío es válido: es un lead que todavía no se tocó.
ESTADOS = (
    "",
    "sin respuesta",
    "descalificado (dq)",
    "no interesado",
    "agendado",
    "follow ups (seguimiento)",
    "pitch call negada",
)


class EstadoIn(BaseModel):
    estado: str


@app.patch("/api/dashboard/leads/{lead_id}/estado")
def cambiar_estado(lead_id: int, payload: EstadoIn, key: str = Query(...)):
    _check_dashboard_key(key)
    estado = payload.estado.strip().lower()
    if estado not in ESTADOS:
        raise HTTPException(status_code=400, detail="Ese estado no existe.")
    with get_connection() as conn:
        cur = conn.execute("UPDATE leads SET estado = ? WHERE id = ?", (estado, lead_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ese lead ya no existe.")
        conn.commit()
    return {"id": lead_id, "estado": estado}


@app.delete("/api/dashboard/leads/{lead_id}")
def borrar_lead(lead_id: int, key: str = Query(...)):
    """Borra un lead del panel. No se puede deshacer."""
    _check_dashboard_key(key)
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ese lead ya no existe.")
        # el contador de usos de la clave deja de contar al lead borrado
        conn.execute(
            """
            UPDATE codes SET times_used = (
                SELECT COUNT(*) FROM leads WHERE leads.codigo_usado = codes.code
            )
            """
        )
        conn.commit()
    return {"borrado": lead_id}


# --- Estáticos ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/dashboard")
def serve_dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/")
def serve_root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Catch-all: cualquier /algo-que-sea se sirve como la misma landing.
# El slug se lee del lado del cliente (window.location.pathname).
# Va al final para no pisar /api, /static, /dashboard.
@app.get("/{slug}")
def serve_landing_with_slug(slug: str) -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
