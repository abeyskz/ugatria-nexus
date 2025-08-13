-- Initialize pgvector extension and database for Tesumi System v2.0

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create custom indexes for better performance
-- (Tables will be created by SQLAlchemy, but we can pre-configure some settings)

-- Set up connection parameters for better performance
ALTER SYSTEM SET shared_preload_libraries = 'vector';
ALTER SYSTEM SET max_connections = 200;

-- Optimization for vector operations
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET effective_cache_size = '4GB';

-- Reload configuration
SELECT pg_reload_conf();
