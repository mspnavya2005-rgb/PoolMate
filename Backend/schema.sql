-- OPTIONAL: MySQL schema. The backend auto-creates these tables via SQLAlchemy,
-- you only need to create the (empty) database:
--   CREATE DATABASE carpool_db CHARACTER SET utf8mb4;
-- then set DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/carpool_db
-- The statements below show the equivalent structure (useful for documentation / viva).

CREATE DATABASE IF NOT EXISTS carpool_db CHARACTER SET utf8mb4;
USE carpool_db;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  phone VARCHAR(20),
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('driver','passenger') NOT NULL,
  pref_ac BOOLEAN DEFAULT FALSE,
  pref_no_smoking BOOLEAN DEFAULT TRUE,
  pref_music BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rides (
  id INT AUTO_INCREMENT PRIMARY KEY,
  driver_id INT NOT NULL,
  pickup VARCHAR(80) NOT NULL,
  destination VARCHAR(80) NOT NULL,
  depart_time DATETIME NOT NULL,
  seats_total INT NOT NULL,
  seats_available INT NOT NULL,
  price_per_seat FLOAT DEFAULT 0,
  vehicle VARCHAR(80),
  has_ac BOOLEAN DEFAULT TRUE,
  smoking_allowed BOOLEAN DEFAULT FALSE,
  music BOOLEAN DEFAULT TRUE,
  status VARCHAR(12) DEFAULT 'open',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (driver_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ride_id INT NOT NULL,
  passenger_id INT NOT NULL,
  seats INT DEFAULT 1,
  pickup_point VARCHAR(80) NOT NULL,
  drop_point VARCHAR(80) NOT NULL,
  status VARCHAR(12) DEFAULT 'confirmed',
  match_label VARCHAR(20),
  match_score INT DEFAULT 0,
  rating INT,
  review VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ride_id) REFERENCES rides(id),
  FOREIGN KEY (passenger_id) REFERENCES users(id)
);
