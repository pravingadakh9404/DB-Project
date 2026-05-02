CREATE TABLE IF NOT EXISTS concerts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    date TIMESTAMP NOT NULL,
    total_seats INT NOT NULL,
    available_seats INT NOT NULL,
    price NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    concert_id INT REFERENCES concerts(id),
    user_name VARCHAR(255) NOT NULL,
    tickets_booked INT NOT NULL
);

-- Truncate if re-running
TRUNCATE bookings, concerts RESTART IDENTITY CASCADE;

INSERT INTO concerts (name, date, total_seats, available_seats, price) VALUES
('Neon Frequencies ft. AR Rahman',     '2025-08-15 19:00:00', 500,  500,  1299.00),
('Coldplay World Tour – Mumbai',        '2025-09-22 20:00:00', 1000, 1000, 4999.00),
('Electronic Nights: Daft Punk Tribute','2025-10-10 21:00:00', 300,  300,  899.00),
('Arijit Singh Live – Dil Se',          '2025-11-05 19:30:00', 800,  800,  2499.00),
('Prateek Kuhad Acoustic Sessions',     '2025-11-28 18:00:00', 200,  200,  699.00),
('Sunburn Arena: Martin Garrix',        '2025-12-20 22:00:00', 1500, 1500, 3499.00);
