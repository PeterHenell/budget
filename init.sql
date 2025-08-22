-- Budget App Database Initialization Script
-- This script sets up the initial database schema and data

-- Enable extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The schema is created by the application, but we can add any
-- additional setup here if needed

-- Create indexes for better performance (if not already created by app)
-- These will be created by the application, but listing here for reference:
-- CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
-- CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
-- CREATE INDEX IF NOT EXISTS idx_transactions_year_month ON transactions(year, month);

-- Grant necessary permissions (already handled by POSTGRES_USER)
