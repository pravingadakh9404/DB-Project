import os
from urllib.parse import quote_plus
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE URL CONSTRUCTION
# BUG FIX 1: Must use "postgresql+psycopg2://" prefix — plain "postgresql://"
#            makes SQLAlchemy crash with "Could not load backend 'psycopg2'"
# BUG FIX 2: Password URL-encoded via quote_plus() to handle special chars
# ─────────────────────────────────────────────────────────────────────────────

_raw_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:aXAVHLQtPXhMCC8l@db.owoajhmwxqtqjxxlkgiv.supabase.co:5432/postgres")

if not _raw_url:
    # Fallback: build from individual parts
    _user     = os.environ.get("DB_USER",     "postgres")
    _password = os.environ.get("DB_PASSWORD", "aXAVHLQtPXhMCC8l")
    _host     = os.environ.get("DB_HOST",     "db.owoajhmwxqtqjxxlkgiv.supabase.co")
    _port     = os.environ.get("DB_PORT",     "5432")
    _name     = os.environ.get("DB_NAME",     "postgres")
    DATABASE_URL = f"postgresql+psycopg2://{_user}:{quote_plus(_password)}@{_host}:{_port}/{_name}"
else:
    # Fix prefix if env var was set without +psycopg2
    if _raw_url.startswith("postgresql://") and "+psycopg2" not in _raw_url:
        _raw_url = _raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    DATABASE_URL = _raw_url

# ─────────────────────────────────────────────────────────────────────────────
# ENGINE
# BUG FIX 4: Wrap in try/except — startup errors now show clearly in Render logs
# pool_pre_ping: auto-reconnect if Supabase drops idle connection
# ─────────────────────────────────────────────────────────────────────────────
try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000"
        }
    )
except Exception as e:
    raise RuntimeError(f"Failed to create DB engine: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="SoundStage Ticket Booking")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# BUG FIX 3: SQLAlchemy returns datetime + Decimal objects that JSON can't
# serialize. This converts every value in a row dict to a safe type.
# ─────────────────────────────────────────────────────────────────────────────
def safe_dict(row) -> dict:
    result = {}
    for k, v in dict(row).items():
        if hasattr(v, "isoformat"):     # datetime / date / time
            result[k] = v.isoformat()
        elif hasattr(v, "__float__"):   # Decimal (price column)
            result[k] = float(v)
        else:
            result[k] = v
    return result

# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────
class BookingRequest(BaseModel):
    concert_id: int
    user_name: str
    tickets_booked: int

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("index.html")


@app.get("/health")
def health():
    """DB connectivity check — open /health in browser to diagnose."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.get("/concerts")
def get_concerts():
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM concerts ORDER BY date ASC")
            ).mappings().all()
            return [safe_dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@app.post("/book")
def book_ticket(req: BookingRequest):
    try:
        with engine.begin() as conn:
            concert = conn.execute(
                text("SELECT available_seats FROM concerts WHERE id = :id"),
                {"id": req.concert_id}
            ).mappings().first()

            if not concert:
                raise HTTPException(status_code=404, detail="Concert not found")
            if concert["available_seats"] < req.tickets_booked:
                raise HTTPException(
                    status_code=400,
                    detail=f"Only {concert['available_seats']} seat(s) left"
                )

            conn.execute(
                text("UPDATE concerts SET available_seats = available_seats - :t WHERE id = :id"),
                {"t": req.tickets_booked, "id": req.concert_id}
            )
            conn.execute(
                text("INSERT INTO bookings (concert_id, user_name, tickets_booked) VALUES (:cid, :name, :t)"),
                {"cid": req.concert_id, "name": req.user_name, "t": req.tickets_booked}
            )
            return {"message": "Booking confirmed!"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")


@app.get("/bookings")
def get_bookings():
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT b.id, b.user_name, b.tickets_booked, c.name AS concert_name
                    FROM bookings b
                    JOIN concerts c ON b.concert_id = c.id
                    ORDER BY b.id DESC
                """)
            ).mappings().all()
            return [safe_dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
