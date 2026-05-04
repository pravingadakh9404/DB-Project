```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text

DB_URL = "postgresql://neondb_owner:npg_g5PVY8qCDiLE@ep-green-smoke-ambio3mk-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DB_URL)

app = FastAPI()

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

class ConcertCreate(BaseModel):
    name: str
    date: str
    price: int
    available_seats: int

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/concerts")
def concerts():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM concerts ORDER BY date")).mappings().all()
        return [dict(r) for r in rows]

@app.post("/book")
def book(req: BookingRequest):
    with engine.begin() as conn:
        c = conn.execute(text("SELECT available_seats FROM concerts WHERE id=:id"), {"id":req.concert_id}).mappings().first()

        if not c or c["available_seats"] < req.tickets_booked:
            raise HTTPException(400, "Not enough seats")

        conn.execute(text("UPDATE concerts SET available_seats=available_seats-:t WHERE id=:id"),
                     {"t":req.tickets_booked,"id":req.concert_id})

        conn.execute(text("INSERT INTO bookings(concert_id,user_name,tickets_booked) VALUES(:c,:u,:t)"),
                     {"c":req.concert_id,"u":req.user_name,"t":req.tickets_booked})

    return {"msg":"ok"}

@app.get("/bookings")
def bookings():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT b.*,c.name as concert_name FROM bookings b JOIN concerts c ON b.concert_id=c.id")).mappings().all()
        return [dict(r) for r in rows]

@app.post("/add-concert")
def add(concert: ConcertCreate):
    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO concerts (name,date,total_seats,available_seats,price)
        VALUES (:n,:d,:t,:a,:p)
        """),{
            "n":concert.name,
            "d":concert.date,
            "t":concert.available_seats,
            "a":concert.available_seats,
            "p":concert.price
        })
    return {"msg":"added"}
```
