-- ============================================================================
-- RAG Application - Cortex Search Service Creation
-- ============================================================================
-- Purpose: Create and configure Cortex Search Service for RAG
-- PREREQUISITE: Run 00_setup_snowflake.sql and 01_cortex_schema.sql first!
-- ============================================================================

-- Use the RAG role and warehouse
USE ROLE RAG_ROLE;
USE WAREHOUSE RAG_WH;
USE DATABASE RAG_DB;
USE SCHEMA PUBLIC;

-- ============================================================================
-- Enable Cross-Region Inference (if needed)
-- ============================================================================
-- Check current cross-region setting
SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION' IN ACCOUNT;

-- If you need to enable cross-region inference (requires ACCOUNTADMIN):
-- ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';

-- Note: Cross-region inference may have higher latency and costs

-- ============================================================================
-- Create Cortex Search Service
-- ============================================================================
-- This creates a fully managed search service that:
-- 1. Automatically embeds CHUNK_TEXT
-- 2. Creates searchable index with hybrid search (vector + keyword)
-- 3. Auto-refreshes when source data changes
-- 4. Provides low-latency retrieval for RAG

CREATE CORTEX SEARCH SERVICE IF NOT EXISTS MEETING_NOTES_SEARCH
ON CHUNK_TEXT  -- Column to embed and search
ATTRIBUTES DOCUMENT_ID, FILENAME, CHUNK_INDEX, UPLOAD_TIME  -- Metadata to return
WAREHOUSE = RAG_WH  -- Warehouse for search queries
TARGET_LAG = '1 minute'  -- Refresh frequency (how often to update index)
AS (
    SELECT 
        CHUNK_ID,          -- Unique identifier for each chunk
        CHUNK_TEXT,        -- Text to embed and search (required)
        DOCUMENT_ID,       -- Metadata: which document
        FILENAME,          -- Metadata: source filename
        CHUNK_INDEX,       -- Metadata: chunk position
        UPLOAD_TIME        -- Metadata: when uploaded
    FROM DOCUMENT_CHUNKS
);

-- ============================================================================
-- Verify Search Service Created
-- ============================================================================

-- Show all Cortex Search Services
SHOW CORTEX SEARCH SERVICES;

-- Describe the search service
DESC CORTEX SEARCH SERVICE MEETING_NOTES_SEARCH;

-- ============================================================================
-- Test Search Service (after uploading documents)
-- ============================================================================

-- Basic search test
-- Returns top 5 most relevant chunks
/*
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'MEETING_NOTES_SEARCH',
    '{
        "query": "What were the action items?",
        "columns": ["CHUNK_TEXT", "DOCUMENT_ID", "FILENAME", "CHUNK_INDEX"],
        "limit": 5
    }'
) AS search_results;
*/

-- Search with filters
-- Filter by specific document
/*
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'MEETING_NOTES_SEARCH',
    '{
        "query": "What were the action items?",
        "columns": ["CHUNK_TEXT", "DOCUMENT_ID", "FILENAME"],
        "filter": {"@eq": {"DOCUMENT_ID": "your-document-id-here"}},
        "limit": 5
    }'
) AS search_results;
*/

-- ============================================================================
-- Refresh Search Service (if needed)
-- ============================================================================

-- Manual refresh (usually automatic based on TARGET_LAG)
-- ALTER CORTEX SEARCH SERVICE MEETING_NOTES_SEARCH REFRESH;

-- ============================================================================
-- Drop Search Service (if you need to recreate)
-- ============================================================================

-- DROP CORTEX SEARCH SERVICE IF EXISTS MEETING_NOTES_SEARCH;

-- ============================================================================
-- Notes on Cortex Search Service Configuration
-- ============================================================================
-- 1. ON CHUNK_TEXT:
--    - Specifies which column contains the text to embed and search
--    - This column is automatically embedded using Cortex
--    - Embeddings are managed internally (you don't see them)
--
-- 2. ATTRIBUTES:
--    - Additional columns to return with search results
--    - These are NOT embedded, just returned as metadata
--    - Useful for filtering and displaying context
--
-- 3. WAREHOUSE:
--    - Specifies which warehouse to use for search queries
--    - Search queries consume compute credits
--    - Use appropriate warehouse size based on query volume
--
-- 4. TARGET_LAG:
--    - How frequently to refresh the search index
--    - '1 minute' = near real-time updates
--    - '1 hour' = less frequent, lower cost
--    - Balance between freshness and cost
--
-- 5. Search Syntax:
--    SNOWFLAKE.CORTEX.SEARCH_PREVIEW('service_name', 'json_params')
--    - json_params: JSON object with query, columns, filter, limit
--    - Returns: JSON with ranked results and metadata
--
-- 6. Hybrid Search:
--    - Combines vector similarity (semantic)
--    - Keyword matching (lexical)
--    - Automatic reranking for best results
--    - No manual tuning needed
--
-- 7. Cost Considerations:
--    - Charged per query (not per document)
--    - Warehouse compute for search queries
--    - Storage for search index
--    - More cost-effective than manual vector search at scale
--
-- 8. Monitoring:
--    - Use SHOW CORTEX SEARCH SERVICES for overview
--    - Use DESC CORTEX SEARCH SERVICE for details
--    - Monitor warehouse usage for cost tracking
-- ============================================================================
