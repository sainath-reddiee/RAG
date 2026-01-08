# Snowflake Cortex Function Syntax Reference

## ✅ Correct Syntax for Each Function

### 1. AI_COMPLETE (Named Parameters)
```sql
SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
    model => 'mistral-large2',
    prompt => 'Your question here',
    model_parameters => {
        'max_tokens': 512,
        'temperature': 0.1
    }
) AS answer;
```

**Key Points:**
- **ALL parameters must be named** (model =>, prompt =>, model_parameters =>)
- Cannot mix positional and named
- model_parameters is a JSON object

---

### 2. AI_EMBED (Positional Parameters)
```sql
-- For text
SELECT SNOWFLAKE.CORTEX.AI_EMBED(
    'snowflake-arctic-embed-l-v2.0',
    'Text to embed'
) AS embedding;

-- For images (multimodal)
SELECT SNOWFLAKE.CORTEX.AI_EMBED(
    'voyage-multimodal-3',
    TO_FILE('@my_images', 'image.png')
) AS embedding;
```

**Key Points:**
- **Uses positional parameters** (NOT named)
- First parameter: model name
- Second parameter: content (text or TO_FILE for images)

---

### 3. SPLIT_TEXT_RECURSIVE_CHARACTER (Positional Parameters)

**Standalone Query:**
```sql
-- Direct SELECT (returns array/table)
SELECT SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER(
    'Text to chunk',
    'none',
    1000,
    200
);
```

**In LATERAL JOIN (for views/queries):**
```sql
SELECT 
    doc_id,
    c.value
FROM documents,
LATERAL FLATTEN(input => SNOWFLAKE.CORTEX.SPLIT_TEXT_RECURSIVE_CHARACTER(
    document_text,
    'none',
    1000,
    200
)) c;
```

**Key Points:**
- Standalone: Direct SELECT (no FROM)
- In queries: Use `LATERAL FLATTEN(input => ...)`
- Parameters: text, format, chunk_size, overlap
- Format: 'none' or 'markdown'
- Separators parameter exists but is OPTIONAL (not commonly used)

---

## Summary Table

| Function | Parameter Style | Example |
|----------|----------------|---------|
| **AI_COMPLETE** | Named only | `model => 'x', prompt => 'y', model_parameters => {}` |
| **AI_EMBED** | Positional | `'model', 'content'` |
| **SPLIT_TEXT_RECURSIVE_CHARACTER** | Positional | `'text', 'format', chunk_size, overlap` |

---

## Common Mistakes

❌ **Wrong:** Mixing positional and named for AI_COMPLETE
```sql
AI_COMPLETE('model', 'prompt', max_tokens => 50)  -- ERROR!
```

✅ **Correct:** All named
```sql
AI_COMPLETE(model => 'x', prompt => 'y', model_parameters => {'max_tokens': 50})
```

❌ **Wrong:** Using named parameters for AI_EMBED
```sql
AI_EMBED(model => 'x', content => 'y')  -- ERROR!
```

✅ **Correct:** Positional
```sql
AI_EMBED('model', 'content')
```

---

## References
- [AI_COMPLETE Documentation](https://docs.snowflake.com/en/sql-reference/functions/ai_complete)
- [AI_EMBED Documentation](https://docs.snowflake.com/en/sql-reference/functions/ai_embed)
- [SPLIT_TEXT_RECURSIVE_CHARACTER Documentation](https://docs.snowflake.com/en/sql-reference/functions/split_text_recursive_character)
