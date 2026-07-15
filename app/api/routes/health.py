from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Health-check: confirma que a API está de pé e que o banco de staging responde."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — qualquer falha de conexão vira 503 detalhado
        raise HTTPException(status_code=503, detail=f"Falha ao conectar no banco de staging: {exc}") from exc
    return {"status": "ok", "database": "ok"}
