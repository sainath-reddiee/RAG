-- ============================================================================
-- RAG Application - Complete Snowflake Setup Script
-- ============================================================================
-- Purpose: Complete setup from scratch including database, roles, and grants
-- Run this as ACCOUNTADMIN
-- ============================================================================

-- Switch to ACCOUNTADMIN role
USE ROLE ACCOUNTADMIN;

-- ============================================================================
-- Step 1: Create Database and Schema
-- ============================================================================

-- Create database for RAG application
CREATE DATABASE IF NOT EXISTS RAG_DB
    COMMENT = 'Database for RAG application using Cortex Search Service';

-- Use the database
USE DATABASE RAG_DB;

-- Create schema (using PUBLIC for simplicity)
CREATE SCHEMA IF NOT EXISTS PUBLIC
    COMMENT = 'Main schema for RAG application';

USE SCHEMA PUBLIC;

-- ============================================================================
-- Step 2: Create Warehouse
-- ============================================================================

-- Create dedicated warehouse for RAG application
-- Size: X-SMALL for development, scale up for production
CREATE WAREHOUSE IF NOT EXISTS RAG_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60              -- Suspend after 1 minute of inactivity
    AUTO_RESUME = TRUE             -- Auto-resume when queries are submitted
    INITIALLY_SUSPENDED = TRUE     -- Start suspended to save costs
    COMMENT = 'Warehouse for RAG application queries and Cortex Search Service';

-- ============================================================================
-- Step 3: Create Role for RAG Application
-- ============================================================================

-- Create custom role for RAG application
CREATE ROLE IF NOT EXISTS RAG_ROLE
    COMMENT = 'Role for RAG application with Cortex permissions';

-- Grant role to ACCOUNTADMIN (so you can use it)
GRANT ROLE RAG_ROLE TO ROLE ACCOUNTADMIN;

-- ============================================================================
-- Step 4: Grant Database and Schema Permissions
-- ============================================================================

-- Grant database usage
GRANT USAGE ON DATABASE RAG_DB TO ROLE RAG_ROLE;

-- Grant schema usage and creation
GRANT USAGE ON SCHEMA RAG_DB.PUBLIC TO ROLE RAG_ROLE;
GRANT CREATE TABLE ON SCHEMA RAG_DB.PUBLIC TO ROLE RAG_ROLE;
GRANT CREATE VIEW ON SCHEMA RAG_DB.PUBLIC TO ROLE RAG_ROLE;
GRANT CREATE CORTEX SEARCH SERVICE ON SCHEMA RAG_DB.PUBLIC TO ROLE RAG_ROLE;

-- Grant all privileges on future tables and views
GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA RAG_DB.PUBLIC TO ROLE RAG_ROLE;
GRANT ALL PRIVILEGES ON FUTURE VIEWS IN SCHEMA RAG_DB.PUBLIC TO ROLE RAG_ROLE;

-- ============================================================================
-- Step 5: Grant Warehouse Permissions
-- ============================================================================

-- Grant warehouse usage
GRANT USAGE ON WAREHOUSE RAG_WH TO ROLE RAG_ROLE;
GRANT OPERATE ON WAREHOUSE RAG_WH TO ROLE RAG_ROLE;

-- ============================================================================
-- Step 6: Grant Cortex Permissions
-- ============================================================================

-- Grant Cortex AI permissions using database roles
-- The CORTEX_USER database role provides access to all Cortex AI functions

-- Method 1: Grant CORTEX_USER database role (Recommended)
-- This grants access to all Cortex functions (AI_COMPLETE, AI_EMBED, etc.)
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE RAG_ROLE;

-- Optional: If you want more granular control, you can grant specific database roles:
-- GRANT DATABASE ROLE SNOWFLAKE.CORTEX_EMBED_USER TO ROLE RAG_ROLE;  -- For embedding functions only

-- Note: By default, CORTEX_USER is granted to PUBLIC role
-- For production, consider revoking from PUBLIC and granting to specific roles:
-- REVOKE DATABASE ROLE SNOWFLAKE.CORTEX_USER FROM ROLE PUBLIC;
-- GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE RAG_ROLE;

-- ============================================================================
-- Step 7: Enable Cross-Region Inference (Optional - if needed)
-- ============================================================================

-- Cross-region inference allows using Cortex services even if specific models
-- are not available in your region. This may incur additional data transfer costs.

-- IMPORTANT: This can ONLY be set at ACCOUNT level by ACCOUNTADMIN
-- Cannot be set at session or user level

-- First, check current setting
SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION' IN ACCOUNT;

-- Options for CORTEX_ENABLED_CROSS_REGION:
-- 1. 'DISABLED' (default) - Only use your account's region
-- 2. 'ANY_REGION' - Allow any Snowflake region that supports cross-region inference
-- 3. Specific region(s) - e.g., 'AWS_US_WEST_2' or 'AWS_US_WEST_2,AWS_EU_CENTRAL_1'

-- Enable cross-region inference for any region (most permissive):
-- ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';

-- Or enable for specific regions only:
-- ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'AWS_US_WEST_2';

-- To disable (revert to default):
-- ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'DISABLED';

-- Note: Cross-region inference considerations:
-- - Higher latency (requests go to different region)
-- - Additional data transfer costs
-- - Data stays within cloud provider network (AWS to AWS, etc.)
-- - User inputs/outputs are not stored or cached during cross-region inference

-- ============================================================================
-- Step 8: Verification
-- ============================================================================

-- Show created objects
SHOW DATABASES LIKE 'RAG_DB';
SHOW SCHEMAS IN DATABASE RAG_DB;
SHOW WAREHOUSES LIKE 'RAG_WH';
SHOW ROLES LIKE 'RAG_ROLE';

-- Show grants
SHOW GRANTS TO ROLE RAG_ROLE;

-- Check cross-region setting
SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION' IN ACCOUNT;

-- ============================================================================
-- Step 9: Switch to RAG Role
-- ============================================================================

-- Switch to the RAG role for subsequent operations
USE ROLE RAG_ROLE;
USE WAREHOUSE RAG_WH;
USE DATABASE RAG_DB;
USE SCHEMA PUBLIC;

-- Verify you can use Cortex functions
-- Test AI_COMPLETE function (latest version)
SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
    model => 'mistral-large2',
    prompt => 'Say "Cortex is working!" if you can read this.',
    model_parameters => {
        'max_tokens': 50,
        'temperature': 0.1
    }
) AS test_result;

-- Test AI_EMBED function (latest version for embeddings)
-- AI_EMBED uses positional parameters, not named
SELECT SNOWFLAKE.CORTEX.AI_EMBED(
    'snowflake-arctic-embed-l-v2.0',
    'Test embedding'
) AS test_embedding;

-- Test SPLIT_TEXT_RECURSIVE_CHARACTER function
-- Direct SELECT (no FROM clause)
SELECT SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER(
    'This is a test. This is only a test.',
    'none',
    20,
    5
);

-- ============================================================================
-- Notes
-- ============================================================================
-- 1. Run this script as ACCOUNTADMIN
-- 2. After setup, you can use RAG_ROLE for the application
-- 3. Update your config.yaml to use:
--    - warehouse: RAG_WH
--    - database: RAG_DB
--    - schema: PUBLIC
--    - role: RAG_ROLE (or ACCOUNTADMIN if you prefer)
--
-- 4. Cost Optimization:
--    - Warehouse auto-suspends after 1 minute
--    - Start with X-SMALL, scale up if needed
--    - Monitor Cortex usage for costs
--
-- 5. Cross-Region Inference:
--    - Only enable if specific Cortex models are not available in your region
--    - Check current setting: SHOW PARAMETERS LIKE 'CORTEX_ENABLED_CROSS_REGION'
--    - Be aware of additional costs and latency
--
-- 6. Security:
--    - RAG_ROLE has minimal required permissions
--    - Grant to specific users as needed
--    - Consider creating separate roles for dev/prod
-- ============================================================================

