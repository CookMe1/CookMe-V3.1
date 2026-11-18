"""Collects crashes from the app in people's browsers so the admin can see them."""
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
_hits: dict = {}   # ip -> [timestamps], simple flood guard


class ClientError(BaseModel):
    message: str = ""
    stack: str = ""
    url: str = ""


@router.post("/client-error")
async def client_error(data: ClientError, request: Request):
    ip = request.client.host if request.client else "?"
    now = time.time()
    recent = [t for t in _hits.get(ip, []) if now - t < 60]
    if len(recent) >= 10:
        return {"ok": False}
    _hits[ip] = recent + [now]
    if len(_hits) > 5000:
        _hits.clear()
    await request.app.state.db.client_errors.insert_one({
        "message": data.message[:500], "stack": data.stack[:2000], "url": data.url[:300],
        "agent": request.headers.get("user-agent", "")[:200],
        "created_at": datetime.now(timezone.utc),
    })
    return {"ok": True}
