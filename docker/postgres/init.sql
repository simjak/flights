-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE priceindicator AS ENUM ('LOW', 'TYPICAL', 'HIGH');
CREATE TYPE jobstatus AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

-- Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    departure_airports VARCHAR[] NOT NULL,
    destination_airports VARCHAR[] NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    min_duration_days INTEGER NOT NULL DEFAULT 13,
    max_duration_days INTEGER NOT NULL DEFAULT 30,
    max_price FLOAT NOT NULL DEFAULT 700.0,
    max_stops INTEGER NOT NULL DEFAULT 2,
    max_concurrent_searches INTEGER NOT NULL DEFAULT 3,
    last_checkpoint TIMESTAMP,
    status jobstatus NOT NULL DEFAULT 'pending',
    total_combinations INTEGER NOT NULL DEFAULT 0,
    processed_combinations INTEGER NOT NULL DEFAULT 0,
    progress FLOAT NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create flight_results table
CREATE TABLE IF NOT EXISTS flight_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    departure_airport VARCHAR(3) NOT NULL,
    destination_airport VARCHAR(3) NOT NULL,
    outbound_date DATE NOT NULL,
    return_date DATE,
    price FLOAT NOT NULL,
    airline VARCHAR(100) NOT NULL,
    stops INTEGER NOT NULL,
    duration VARCHAR(20) NOT NULL,
    current_price_indicator priceindicator NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster job lookups
CREATE INDEX IF NOT EXISTS idx_flight_results_job_id ON flight_results(job_id);
CREATE INDEX IF NOT EXISTS idx_flight_results_price ON flight_results(price);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for jobs table
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();