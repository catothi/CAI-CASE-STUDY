-- Drop existing tables if they exist (optional, for a clean start)
-- Make sure to drop in order of dependency or use CASCADE
-- DROP TABLE IF EXISTS reservations CASCADE;
-- DROP TABLE IF EXISTS customers CASCADE;
-- DROP TABLE IF EXISTS tables CASCADE;
-- If you were running this whole script via psql -f script.sql, you'd likely run
-- CREATE DATABASE reservations_db;
-- \c reservations_db  <-- Then the rest of the script would run in the context of the new DB.



CREATE TABLE tables (
    tid SERIAL PRIMARY KEY,                      -- Table ID
    table_number VARCHAR(255) UNIQUE NOT NULL,
    capacity INTEGER NOT NULL
);

CREATE TABLE customers (
    cid SERIAL PRIMARY KEY,                      -- Customer ID
    last_name VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    phone VARCHAR(50) UNIQUE NOT NULL
    -- email VARCHAR(255) UNIQUE -- Consider adding email
);

CREATE TABLE reservations (
    rid SERIAL PRIMARY KEY,                                              -- Reservation ID
    tid INTEGER NOT NULL REFERENCES tables(tid) ON DELETE CASCADE,       -- Foreign Key to tables.tid
    cid INTEGER NOT NULL REFERENCES customers(cid) ON DELETE CASCADE,    -- Foreign Key to customers.cid
    status VARCHAR(50) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'cancelled', 'completed')),
    comment TEXT,
    number_of_people INTEGER NOT NULL,
    reservation_date DATE NOT NULL,
    reservation_time VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    -- Consider adding a unique constraint to prevent double booking for the same table, date, and time
    -- UNIQUE (tid, reservation_date, reservation_time)
);

-- Optional: Trigger to update 'updated_at' timestamp on reservations table
CREATE OR REPLACE FUNCTION update_reservations_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_reservations_updated_at
BEFORE UPDATE ON reservations
FOR EACH ROW
EXECUTE FUNCTION update_reservations_updated_at_column();

-- You might want indexes for performance
CREATE INDEX idx_reservations_date ON reservations(reservation_date);
CREATE INDEX idx_reservations_table_id_date ON reservations(tid, reservation_date);
CREATE INDEX idx_customers_phone ON customers(phone);