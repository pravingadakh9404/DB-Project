import os
from urllib.parse import quote_plus
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel

# ══════════════════════════════════════════════════════════════════
#  DB URL  —  pg8000 (pure Python, no system libs needed on Render)
# ══════════════════════════════════════════════════════════════════
_pw   = quote_plus(os.environ.get("DB_PASSWORD", "aXAVHLQtPXhMCC8l"))
_host = os.environ.get("DB_HOST", "db.owoajhmwxqtqjxxlkgiv.supabase.co")
_user = os.environ.get("DB_USER", "postgres")
_port = os.environ.get("DB_PORT", "5432")
_name = os.environ.get("DB_NAME", "postgres")

# If full DATABASE_URL is set, use it but force pg8000 driver
_raw = os.environ.get("DATABASE_URL", "")
if _raw:
    for pfx in ("postgresql+psycopg2://", "postgresql+psycopg://",
                 "postgresql+pg8000://", "postgresql://", "postgres://"):
        if _raw.startswith(pfx):
            _raw = _raw[len(pfx):]
            break
    DATABASE_URL = f"postgresql+pg8000://{_raw}"
else:
    DATABASE_URL = f"postgresql+pg8000://{_user}:{_pw}@{_host}:{_port}/{_name}"

# ══════════════════════════════════════════════════════════════════
#  ENGINE
# ══════════════════════════════════════════════════════════════════
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=3,
    max_overflow=2,
)

# ══════════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════════
app = FastAPI(title="SoundStage")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# JSON-safe row serialiser (handles datetime, Decimal)
def row_to_dict(row) -> dict:
    out = {}
    for k, v in dict(row).items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif hasattr(v, "__float__"):
            out[k] = float(v)
        else:
            out[k] = v
    return out

class BookingRequest(BaseModel):
    concert_id: int
    user_name: str
    tickets_booked: int

# ══════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return FileResponse("index.html")


@app.get("/health")
def health():
    """Visit /health in browser to instantly diagnose DB issues."""
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected", "url_prefix": DATABASE_URL[:40]}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e), "url_prefix": DATABASE_URL[:40]}
        )


@app.get("/concerts")
def get_concerts():
    try:
        with engine.connect() as c:
            rows = c.execute(text("SELECT * FROM concerts ORDER BY date ASC")).mappings().all()
        return [row_to_dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/book")
def book_ticket(req: BookingRequest):
    try:
        with engine.begin() as c:
            row = c.execute(
                text("SELECT available_seats FROM concerts WHERE id = :id"),
                {"id": req.concert_id}
            ).mappings().first()
            if not row:
                raise HTTPException(404, "Concert not found")
            if row["available_seats"] < req.tickets_booked:
                raise HTTPException(400, f"Only {row['available_seats']} seat(s) left")
            c.execute(
                text("UPDATE concerts SET available_seats = available_seats - :t WHERE id = :id"),
                {"t": req.tickets_booked, "id": req.concert_id}
            )
            c.execute(
                text("INSERT INTO bookings (concert_id, user_name, tickets_booked) VALUES (:cid,:name,:t)"),
                {"cid": req.concert_id, "name": req.user_name, "t": req.tickets_booked}
            )
        return {"message": "Booking confirmed!"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bookings")
def get_bookings():
    try:
        with engine.connect() as c:
            rows = c.execute(text("""
                SELECT b.id, b.user_name, b.tickets_booked, c.name AS concert_name
                FROM bookings b JOIN concerts c ON b.concert_id = c.id
                ORDER BY b.id DESC
            """)).mappings().all()
        return [row_to_dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
