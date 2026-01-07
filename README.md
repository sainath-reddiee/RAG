# RAG Application with Snowflake Cortex Search Service

A production-grade RAG (Retrieval-Augmented Generation) application built **entirely** with Snowflake Cortex services - no external dependencies, no manual vector operations, no Python chunking.

## 🎯 Overview

This application demonstrates a **pure Snowflake Cortex** approach to RAG:
- Upload meeting notes → Automatic chunking, embedding, and indexing
- Ask questions → Hybrid search + LLM generation
- **Zero manual vector operations** - Cortex Search Service handles everything

---

## 🏗️ Architecture

### Cortex Services Used

| Service | Purpose | Benefit |
|---------|---------|---------|
| **SPLIT_TEXT_RECURSIVE_CHARACTER** | Text chunking | Optimized for RAG, hierarchical separators |
| **Cortex Search Service** | Hybrid search | Vector + keyword + reranking, fully managed |
| **COMPLETE** | Answer generation | Access to latest LLMs (Mistral, Claude, Llama, etc.) |

### Data Flow

```
Upload Document
    ↓
DOCUMENTS table (raw content)
    ↓
DOCUMENT_CHUNKS view (auto-chunking via SPLIT_TEXT_RECURSIVE_CHARACTER)
    ↓
Cortex Search Service (auto-embedding + indexing)
    ↓
User Query → Hybrid Search → Retrieved Chunks
    ↓
COMPLETE (LLM) → Answer
```

---

## 📁 Project Structure

```
c:/Users/satyasainath.p/RAG/
├── streamlit_app/
│   └── app.py                      # Streamlit UI
├── python/
│   ├── config.py                   # Configuration management
│   ├── snowflake_client.py         # Connection handler
│   ├── document_processor.py       # Simple document upload
│   └── retrieval.py                # RAG pipeline (Search Service + Complete)
├── sql/
│   ├── 01_cortex_schema.sql        # DOCUMENTS table + DOCUMENT_CHUNKS view
│   └── 02_cortex_search_service.sql # Create Cortex Search Service
├── config.yaml.template            # Configuration template
├── requirements.txt
└── README.md
```

---

## 🚀 Setup Instructions

### Prerequisites

1. **Snowflake Account** with Cortex AI enabled
2. **Python 3.9+**
3. **Warehouse** with sufficient compute

### Step 1: Install Dependencies

```bash
cd c:/Users/satyasainath.p/RAG
pip install -r requirements.txt
```

### Step 2: Configure Snowflake Credentials

```bash
# Copy template
cp config.yaml.template config.yaml

# Edit config.yaml with your credentials
notepad config.yaml
```

**Required fields:**
```yaml
snowflake:
  account: "your-account.snowflakecomputing.com"
  user: "YOUR_USERNAME"
  password: "YOUR_PASSWORD"
  warehouse: "COMPUTE_WH"
  database: "RAG_DB"
  schema: "PUBLIC"
```

### Step 3: Create Database

```sql
-- In Snowflake worksheet
CREATE DATABASE IF NOT EXISTS RAG_DB;
USE DATABASE RAG_DB;
USE SCHEMA PUBLIC;
```

### Step 4: Run SQL Scripts

**Execute in order:**

1. **Create schema:**
   ```sql
   -- Copy and paste contents of sql/01_cortex_schema.sql
   -- Creates DOCUMENTS table and DOCUMENT_CHUNKS view
   ```

2. **Create Cortex Search Service:**
   ```sql
   -- Copy and paste contents of sql/02_cortex_search_service.sql
   -- Creates MEETING_NOTES_SEARCH service
   ```

3. **Verify:**
   ```sql
   SHOW TABLES;  -- Should show DOCUMENTS
   SHOW VIEWS;   -- Should show DOCUMENT_CHUNKS
   SHOW CORTEX SEARCH SERVICES;  -- Should show MEETING_NOTES_SEARCH
   ```

### Step 5: Launch Application

```bash
streamlit run streamlit_app/app.py
```

Application opens at `http://localhost:8501`

---

## 💡 How It Works

### 1. Document Upload

**User Action:** Upload TXT file

**What Happens:**
```sql
-- Document inserted into DOCUMENTS table
INSERT INTO DOCUMENTS (DOCUMENT_ID, FILENAME, CONTENT, PROCESSING_STATUS)
VALUES ('uuid', 'meeting.txt', 'content...', 'COMPLETED');

-- DOCUMENT_CHUNKS view automatically chunks using Cortex
SELECT * FROM DOCUMENT_CHUNKS WHERE DOCUMENT_ID = 'uuid';
-- Uses SPLIT_TEXT_RECURSIVE_CHARACTER internally

-- Cortex Search Service automatically:
-- 1. Detects new chunks in view
-- 2. Generates embeddings
-- 3. Updates search index
-- (All happens within TARGET_LAG = '1 minute')
```

### 2. Question Answering

**User Action:** Ask "What were the action items?"

**What Happens:**
```sql
-- Step 1: Search using Cortex Search Service
SELECT * FROM TABLE(
    MEETING_NOTES_SEARCH!SEARCH('What were the action items?', 5)
);
-- Returns top 5 chunks via hybrid search (vector + keyword + reranking)

-- Step 2: Generate answer using Cortex Complete
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'mistral-large2',
    'Context: [chunks]\n\nQuestion: What were the action items?\n\nAnswer:',
    {'max_tokens': 512, 'temperature': 0.1}
) AS answer;
```

---

## 🔑 Key Features

### Cortex Search Service Benefits

✅ **Hybrid Search:** Combines vector similarity + keyword matching + reranking
✅ **Fully Managed:** No infrastructure management
✅ **Auto-Scaling:** Handles load automatically
✅ **Real-Time Updates:** TARGET_LAG = '1 minute'
✅ **Cost-Effective:** Pay per query, not storage

### vs. Manual Vector Search

| Feature | Manual Approach | Cortex Search Service |
|---------|----------------|----------------------|
| Chunking | Python code | SPLIT_TEXT_RECURSIVE_CHARACTER |
| Embeddings | Manual SQL | Automatic |
| Storage | EMBEDDINGS table | Managed internally |
| Search | Manual similarity | Hybrid (vector+keyword) |
| Reranking | None | Automatic |
| Infrastructure | Self-managed | Fully managed |

---

## 📊 Database Schema

### DOCUMENTS Table
```sql
CREATE TABLE DOCUMENTS (
    DOCUMENT_ID VARCHAR(36) PRIMARY KEY,
    FILENAME VARCHAR(500) NOT NULL,
    CONTENT TEXT NOT NULL,
    UPLOAD_TIME TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PROCESSING_STATUS VARCHAR(50) DEFAULT 'PENDING'
);
```

### DOCUMENT_CHUNKS View
```sql
CREATE VIEW DOCUMENT_CHUNKS AS
SELECT 
    d.DOCUMENT_ID,
    d.FILENAME,
    UUID_STRING() AS CHUNK_ID,
    c.INDEX AS CHUNK_INDEX,
    c.VALUE AS CHUNK_TEXT,
    c.START_OFFSET,
    c.END_OFFSET
FROM DOCUMENTS d,
LATERAL SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER(
    d.CONTENT,
    1000,  -- chunk_size
    200,   -- chunk_overlap
    ARRAY_CONSTRUCT('\n\n', '\n', '. ', ' ')  -- separators
) c
WHERE d.PROCESSING_STATUS = 'COMPLETED';
```

### Cortex Search Service
```sql
CREATE CORTEX SEARCH SERVICE MEETING_NOTES_SEARCH
ON CHUNK_TEXT
ATTRIBUTES DOCUMENT_ID, FILENAME, CHUNK_INDEX
WAREHOUSE = COMPUTE_WH
TARGET_LAG = '1 minute'
AS (SELECT CHUNK_ID, CHUNK_TEXT, DOCUMENT_ID, FILENAME, CHUNK_INDEX FROM DOCUMENT_CHUNKS);
```

---

## 🛠️ Configuration

### Chunking (SPLIT_TEXT_RECURSIVE_CHARACTER)
- **chunk_size:** 1000 characters (~200 tokens)
- **chunk_overlap:** 200 characters (20%)
- **separators:** `['\n\n', '\n', '. ', ' ']` (hierarchical)

### Search (Cortex Search Service)
- **top_k:** 5 chunks
- **search_method:** Hybrid (vector + keyword + reranking)
- **refresh:** TARGET_LAG = '1 minute'

### Generation (COMPLETE)
- **model:** mistral-large2
- **max_tokens:** 512
- **temperature:** 0.1 (deterministic)

---

## 💰 Cost Considerations

**Cortex Search Service:**
- Charged per query (not per document)
- Warehouse compute for search
- More cost-effective at scale than manual vector search

**Optimization Tips:**
- Use appropriate warehouse size
- Adjust TARGET_LAG based on freshness needs
- Monitor query patterns

---

## ⚠️ Limitations

1. **File Format:** TXT only (PDF support via PARSE_DOCUMENT - future)
2. **Single-User:** No authentication/multi-tenancy
3. **No Document Management:** Can't delete via UI
4. **Basic UI:** Streamlit-based (production would use custom frontend)

---

## 🚀 Next Steps

### Short-term
- [ ] Add PDF support using `PARSE_DOCUMENT`
- [ ] Document management UI (delete, update)
- [ ] Query history persistence

### Medium-term
- [ ] User authentication
- [ ] Advanced search filters
- [ ] Analytics dashboard
- [ ] Multi-document conversations

### Long-term
- [ ] Deploy to Snowpark Container Services
- [ ] Production frontend (React/Next.js)
- [ ] Enterprise features (RBAC, audit logs)

---

## 📚 References

- [Cortex Search Service Docs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search)
- [SPLIT_TEXT_RECURSIVE_CHARACTER](https://docs.snowflake.com/en/sql-reference/functions/split_text_recursive_character)
- [COMPLETE Function](https://docs.snowflake.com/en/sql-reference/functions/complete)
- [Cortex LLM Functions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)

---

## ✨ Key Takeaways

**This is the CORRECT way to build RAG in Snowflake:**
- ✅ Use Cortex Search Service (not manual vector search)
- ✅ Use SPLIT_TEXT_RECURSIVE_CHARACTER (not Python chunking)
- ✅ Use COMPLETE for generation
- ✅ Let Snowflake handle infrastructure

**Result:** Simpler, faster, more scalable, production-ready RAG application!

---

**Built with ❤️ using pure Snowflake Cortex**
