# SQL Scripts Execution Order

Run these scripts in order to set up your Snowflake environment for the RAG application.

## Prerequisites
- Snowflake account with ACCOUNTADMIN access
- Cortex AI enabled (or cross-region inference available)

---

## Step 1: Complete Setup (Run as ACCOUNTADMIN)

**File:** `00_setup_snowflake.sql`

**What it does:**
- Creates `RAG_DB` database
- Creates `RAG_WH` warehouse (X-SMALL, auto-suspend)
- Creates `RAG_ROLE` with minimal required permissions
- Grants Cortex permissions
- Sets up cross-region inference (if needed)
- Verifies Cortex availability

**Run in Snowflake worksheet:**
```sql
-- Copy and paste entire contents of 00_setup_snowflake.sql
```

**Expected output:**
- Database, warehouse, and role created
- Cortex test queries succeed
- `SYSTEM$CORTEX_AVAILABILITY()` returns availability status

---

## Step 2: Create Schema (Run as RAG_ROLE)

**File:** `01_cortex_schema.sql`

**What it does:**
- Creates `DOCUMENTS` table
- Creates `DOCUMENT_CHUNKS` view with `SPLIT_TEXT_RECURSIVE_CHARACTER`
- Verifies table and view creation

**Run in Snowflake worksheet:**
```sql
-- Copy and paste entire contents of 01_cortex_schema.sql
```

**Expected output:**
- `DOCUMENTS` table created
- `DOCUMENT_CHUNKS` view created
- `SHOW TABLES` and `SHOW VIEWS` display the objects

---

## Step 3: Create Cortex Search Service (Run as RAG_ROLE)

**File:** `02_cortex_search_service.sql`

**What it does:**
- Checks Cortex availability
- Enables cross-region inference if needed
- Creates `MEETING_NOTES_SEARCH` Cortex Search Service
- Verifies service creation

**Run in Snowflake worksheet:**
```sql
-- Copy and paste entire contents of 02_cortex_search_service.sql
```

**Expected output:**
- Cortex Search Service `MEETING_NOTES_SEARCH` created
- `SHOW CORTEX SEARCH SERVICES` displays the service
- Service status shows as active

---

## Verification

After running all scripts, verify everything is set up:

```sql
-- Switch to RAG role
USE ROLE RAG_ROLE;
USE WAREHOUSE RAG_WH;
USE DATABASE RAG_DB;
USE SCHEMA PUBLIC;

-- Check tables
SHOW TABLES;
-- Should show: DOCUMENTS

-- Check views
SHOW VIEWS;
-- Should show: DOCUMENT_CHUNKS

-- Check Cortex Search Services
SHOW CORTEX SEARCH SERVICES;
-- Should show: MEETING_NOTES_SEARCH

-- Test Cortex functions
SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
    model => 'mistral-large2',
    prompt => 'Say hello!',
    model_parameters => {'max_tokens': 10}
);
```

---

## Configuration Update

After setup, update your `config.yaml` or `.env`:

```yaml
snowflake:
  account: "BPXADHC-GD29924"
  user: "SAINATH"
  password: "your_password"
  warehouse: "RAG_WH"        # ← Use the new warehouse
  database: "RAG_DB"
  schema: "PUBLIC"
  role: "RAG_ROLE"           # ← Use the new role (or ACCOUNTADMIN)
```

Or in `.env`:
```
SNOWFLAKE_WAREHOUSE=RAG_WH
SNOWFLAKE_ROLE=RAG_ROLE
```

---

## Troubleshooting

### Issue: Cortex functions not available
**Solution:** Enable cross-region inference:
```sql
ALTER SESSION SET CORTEX_ENABLED_CROSS_REGION = TRUE;
```

### Issue: Permission denied
**Solution:** Make sure you're using the correct role:
```sql
USE ROLE RAG_ROLE;
-- or
USE ROLE ACCOUNTADMIN;
```

### Issue: Cortex Search Service creation fails
**Solution:** Check grants:
```sql
SHOW GRANTS TO ROLE RAG_ROLE;
-- Should include CREATE CORTEX SEARCH SERVICE
```

---

## Cost Optimization

- **Warehouse:** X-SMALL auto-suspends after 1 minute
- **Cortex Search:** Charged per query
- **Cross-region:** May incur data transfer costs

Monitor usage:
```sql
-- Check warehouse usage
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE WAREHOUSE_NAME = 'RAG_WH'
ORDER BY START_TIME DESC
LIMIT 10;
```

---

## Next Steps

1. ✅ Run all SQL scripts
2. ✅ Update config.yaml with new warehouse and role
3. ✅ Launch Streamlit app: `streamlit run streamlit_app/app.py`
4. ✅ Upload test document
5. ✅ Ask questions!
