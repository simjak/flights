-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed');
CREATE TYPE price_indicator AS ENUM ('low', 'typical', 'high');

-- Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status job_status NOT NULL DEFAULT 'pending',
    total_tasks INTEGER NOT NULL DEFAULT 0,
    completed_tasks INTEGER NOT NULL DEFAULT 0,
    found_flights INTEGER NOT NULL DEFAULT 0,
    best_price DECIMAL(10,2),
    last_checkpoint JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create flight_results table
CREATE TABLE IF NOT EXISTS flight_results (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    departure_airport VARCHAR(3) NOT NULL,
    destination_airport VARCHAR(3) NOT NULL,
    outbound_date DATE NOT NULL,
    return_date DATE NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    airline VARCHAR(100) NOT NULL,
    stops INTEGER NOT NULL,
    duration VARCHAR(20) NOT NULL,
    current_price_indicator price_indicator NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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