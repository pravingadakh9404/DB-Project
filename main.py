from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel

DATABASE_URL = "postgresql://postgres:[YOUR-PASSWORD]@db.mykozwwwpswzukwzcvei.supabase.co:5432/postgres"
engine = create_engine(DATABASE_URL)
app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class BookingRequest(BaseModel):
    concert_id: int
    user_name: str
    tickets_booked: int

@app.get("/concerts")
def get_concerts():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM concerts ORDER BY date")).mappings().all()
        return [dict(r) for r in rows]

@app.post("/book")
def book_ticket(req: BookingRequest):
    with engine.begin() as conn:
        concert = conn.execute(text("SELECT available_seats FROM concerts WHERE id=:id"), {"id": req.concert_id}).mappings().first()
        if not concert:
            raise HTTPException(status_code=404, detail="Concert not found")
        if concert["available_seats"] < req.tickets_booked:
            raise HTTPException(status_code=400, detail="Not enough seats")
        conn.execute(text("UPDATE concerts SET available_seats=available_seats-:t WHERE id=:id"), {"t": req.tickets_booked, "id": req.concert_id})
        conn.execute(text("INSERT INTO bookings(concert_id,user_name,tickets_booked) VALUES(:cid,:name,:t)"), {"cid": req.concert_id, "name": req.user_name, "t": req.tickets_booked})
        return {"message": "Booking confirmed!"}

@app.get("/bookings")
def get_bookings():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT b.*, c.name as concert_name FROM bookings b JOIN concerts c ON b.concert_id=c.id")).mappings().all()
        return [dict(r) for r in rows]
