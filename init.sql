-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS btcdb;

-- Switch to the database
USE btcdb;

-- Create table for storing generated public addresses
CREATE TABLE IF NOT EXISTS public_addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    address VARCHAR(255) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
