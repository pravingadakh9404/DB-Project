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

INSERT INTO concerts (name, date, total_seats, available_seats, price) VALUES
('Neon Frequencies ft. AR Rahman', '2025-08-15 19:00:00', 500, 500, 1299.00),
('Coldplay World Tour – Mumbai', '2025-09-22 20:00:00', 1000, 1000, 4999.00),
('Electronic Nights: Daft Punk Tribute', '2025-10-10 21:00:00', 300, 300, 899.00);
