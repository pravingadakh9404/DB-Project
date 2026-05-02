from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text

# Hardcoded DB URL with psycopg2 adapter
DB_URL = "postgresql+psycopg2://postgres:aXAVHLQtPXhMCC8l@db.owoajhmwxqtqjxxlkgiv.supabase.co:5432/postgres"
engine = create_engine(DB_URL)

app = FastAPI()

# Add CORS to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BookingRequest(BaseModel):
    concert_id: int
    user_name: str
    tickets_booked: int

# Serve the Frontend HTML
@app.get("/")
def serve_home():
    return FileResponse("index.html")

# API Endpoints
@app.get("/concerts")
def get_concerts():
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT * FROM concerts ORDER BY date")).mappings().all()
            return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/book")
def book_ticket(req: BookingRequest):
    try:
        with engine.begin() as conn:
            concert = conn.execute(text("SELECT available_seats FROM concerts WHERE id=:id"), {"id": req.concert_id}).mappings().first()
            
            if not concert:
                raise HTTPException(status_code=404, detail="Concert not found")
            if concert["available_seats"] < req.tickets_booked:
                raise HTTPException(status_code=400, detail="Not enough seats available")
            
            # Update seats and insert booking
            conn.execute(text("UPDATE concerts SET available_seats=available_seats-:t WHERE id=:id"), {"t": req.tickets_booked, "id": req.concert_id})
            conn.execute(text("INSERT INTO bookings(concert_id, user_name, tickets_booked) VALUES(:cid, :name, :t)"), {"cid": req.concert_id, "name": req.user_name, "t": req.tickets_booked})
            
            return {"message": "Booking successful!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bookings")
def get_bookings():
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT b.id, b.user_name, b.tickets_booked, c.name as concert_name FROM bookings b JOIN concerts c ON b.concert_id = c.id")).mappings().all()
            return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
