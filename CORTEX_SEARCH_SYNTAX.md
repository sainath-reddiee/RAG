# Cortex Search Service - Correct Syntax Reference

## ✅ Correct Syntax (2026)

### Creating a Search Service

```sql
CREATE CORTEX SEARCH SERVICE IF NOT EXISTS MEETING_NOTES_SEARCH
ON CHUNK_TEXT
ATTRIBUTES DOCUMENT_ID, FILENAME, CHUNK_INDEX, UPLOAD_TIME
WAREHOUSE = RAG_WH
TARGET_LAG = '1 minute'
AS (
    SELECT 
        CHUNK_ID,
        CHUNK_TEXT,
        DOCUMENT_ID,
        FILENAME,
        CHUNK_INDEX,
        UPLOAD_TIME
    FROM DOCUMENT_CHUNKS
);
```

### Querying a Search Service

**Basic Query:**
```sql
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'MEETING_NOTES_SEARCH',
    '{
        "query": "What were the action items?",
        "columns": ["CHUNK_TEXT", "DOCUMENT_ID", "FILENAME", "CHUNK_INDEX"],
        "limit": 5
    }'
) AS search_results;
```

**With Filters:**
```sql
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'MEETING_NOTES_SEARCH',
    '{
        "query": "action items",
        "columns": ["CHUNK_TEXT", "FILENAME"],
        "filter": {"@eq": {"DOCUMENT_ID": "doc-123"}},
        "limit": 3
    }'
) AS search_results;
```

**Python Example:**
```python
import json

# Build query parameters
query_params = {
    "query": "What were the action items?",
    "columns": ["CHUNK_TEXT", "DOCUMENT_ID", "FILENAME", "CHUNK_INDEX"],
    "limit": 5
}

# Convert to JSON string
query_params_json = json.dumps(query_params)

# Execute query
query = """
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'MEETING_NOTES_SEARCH',
    %s
) AS search_results
"""

result = cursor.execute(query, (query_params_json,))

# Parse results
search_data = json.loads(result[0]['SEARCH_RESULTS'])
results = search_data.get('results', [])
```

---

## ❌ Old Syntax (Deprecated)

**DO NOT USE:**
```sql
-- This syntax is WRONG
SELECT * FROM TABLE(
    MEETING_NOTES_SEARCH!SEARCH('query', 5)
);
```

---

## Key Differences

| Aspect | Old Syntax | New Syntax |
|--------|-----------|------------|
| Function | `!SEARCH()` | `SNOWFLAKE.CORTEX.SEARCH_PREVIEW()` |
| Parameters | Positional (query, limit) | JSON object |
| Filters | WHERE clause | JSON filter object |
| Columns | SELECT * | Specify in JSON |
| Returns | Table rows | JSON object |

---

## Filter Syntax

**Equality:**
```json
{"@eq": {"DOCUMENT_ID": "doc-123"}}
```

**Multiple conditions (AND):**
```json
{"@and": [
    {"@eq": {"DOCUMENT_ID": "doc-123"}},
    {"@eq": {"FILENAME": "notes.txt"}}
]}
```

**Multiple conditions (OR):**
```json
{"@or": [
    {"@eq": {"DOCUMENT_ID": "doc-123"}},
    {"@eq": {"DOCUMENT_ID": "doc-456"}}
]}
```

---

## References

- [CREATE CORTEX SEARCH SERVICE](https://docs.snowflake.com/en/sql-reference/sql/create-cortex-search)
- [Query Cortex Search Service](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/query-cortex-search-service)
- [SEARCH_PREVIEW Function](https://docs.snowflake.com/en/sql-reference/functions/search_preview-snowflake-cortex)
