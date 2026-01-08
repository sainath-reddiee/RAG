-- ============================================================================
-- RAG Application - Cortex Search Service Schema
-- ============================================================================
-- Purpose: Create simplified schema using Snowflake Cortex Search Service
-- This eliminates manual chunking, embedding, and vector search
-- ============================================================================
-- PREREQUISITE: Run 00_setup_snowflake.sql first!
-- ============================================================================

-- Use the RAG role and warehouse
USE ROLE RAG_ROLE;
USE WAREHOUSE RAG_WH;
USE DATABASE RAG_DB;
USE SCHEMA PUBLIC;

-- ============================================================================
-- Table: DOCUMENTS
-- Purpose: Store raw uploaded documents
-- ============================================================================
CREATE TABLE IF NOT EXISTS DOCUMENTS (
    -- Primary key
    DOCUMENT_ID VARCHAR(36) PRIMARY KEY,
    
    -- Document metadata
    FILENAME VARCHAR(500) NOT NULL,
    FILE_SIZE_BYTES NUMBER NOT NULL,
    UPLOAD_TIME TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    -- Raw content (this is what gets chunked and searched)
    CONTENT TEXT NOT NULL,
    
    -- Processing status
    PROCESSING_STATUS VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, COMPLETED, FAILED
    
    -- Audit fields
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

COMMENT ON TABLE DOCUMENTS IS 'Stores raw uploaded documents for Cortex Search Service';

-- ============================================================================
-- View: DOCUMENT_CHUNKS
-- Purpose: Dynamically chunk documents using Cortex function
-- ============================================================================
CREATE OR REPLACE VIEW DOCUMENT_CHUNKS AS
SELECT 
    d.DOCUMENT_ID,
    d.FILENAME,
    d.UPLOAD_TIME,
    -- Generate deterministic chunk ID (required for Cortex Search Service)
    HASH(d.DOCUMENT_ID, c.index) AS CHUNK_ID,
    -- Chunk metadata from Cortex function via FLATTEN
    c.index AS CHUNK_INDEX,
    c.value::STRING AS CHUNK_TEXT,  -- Cast VARIANT to STRING
    c.value:start_offset::INT AS START_OFFSET,
    c.value:end_offset::INT AS END_OFFSET,
    LENGTH(c.value::STRING) AS CHUNK_SIZE
FROM DOCUMENTS d,
-- Use Cortex function with LATERAL FLATTEN
LATERAL FLATTEN(input => SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER(
    d.CONTENT,
    'none',
    1000,
    200
)) c
WHERE d.PROCESSING_STATUS = 'COMPLETED';

COMMENT ON VIEW DOCUMENT_CHUNKS IS 'Dynamically chunks documents using SPLIT_TEXT_RECURSIVE_CHARACTER';

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Show tables
SHOW TABLES;

-- Describe DOCUMENTS table
DESC TABLE DOCUMENTS;

-- Show views
SHOW VIEWS;

-- Test chunking (after inserting a document)
-- SELECT * FROM DOCUMENT_CHUNKS LIMIT 10;

-- ============================================================================
-- Notes on Cortex Search Service Architecture
-- ============================================================================
-- 1. DOCUMENTS table: Stores raw uploaded content
--    - Simple structure, just metadata + content
--    - No manual chunking or embedding storage
--
-- 2. DOCUMENT_CHUNKS view: Dynamic chunking using Cortex
--    - Uses SPLIT_TEXT_RECURSIVE_CHARACTER function
--    - Chunks are computed on-the-fly (not stored)
--    - Optimized for RAG applications
--
-- 3. Cortex Search Service (created in next script):
--    - Automatically indexes CHUNK_TEXT from the view
--    - Generates embeddings automatically
--    - Provides hybrid search (vector + keyword + reranking)
--    - Manages infrastructure and refresh
--
-- 4. No CHUNKS or EMBEDDINGS tables needed:
--    - Cortex Search Service handles everything
--    - Reduces storage and complexity
--    - Auto-scales and optimizes
--
-- 5. Chunking parameters:
--    - chunk_size: 1000 chars (~200 tokens) - good for most use cases
--    - chunk_overlap: 200 chars (20%) - preserves context
--    - separators: Hierarchical (paragraph > line > sentence > word)
--
-- 6. Benefits:
--    - Simpler schema (1 table + 1 view vs 3 tables)
--    - No manual embedding management
--    - Better search quality (hybrid search)
--    - Automatic optimization and scaling
--    - Lower operational overhead
-- ============================================================================
