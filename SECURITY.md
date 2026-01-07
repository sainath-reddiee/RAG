# SECURITY BEST PRACTICES

## ⚠️ IMPORTANT: Never Commit Credentials!

This project uses **two methods** for secure credential management:

### Option 1: Environment Variables (.env file) - RECOMMENDED

1. **Copy the template:**
   ```bash
   cp .env.template .env
   ```

2. **Edit `.env` with your credentials:**
   ```bash
   SNOWFLAKE_ACCOUNT=your-account.snowflakecomputing.com
   SNOWFLAKE_USER=your_username
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_WAREHOUSE=COMPUTE_WH
   SNOWFLAKE_DATABASE=RAG_DB
   SNOWFLAKE_SCHEMA=PUBLIC
   SNOWFLAKE_ROLE=ACCOUNTADMIN
   ```

3. **`.env` is automatically gitignored** - safe from accidental commits

### Option 2: Config YAML (config.yaml)

1. **Copy the template:**
   ```bash
   cp config.yaml.template config.yaml
   ```

2. **Edit `config.yaml` with your credentials**

3. **`config.yaml` is automatically gitignored** - safe from accidental commits

---

## How It Works

The application loads credentials in this order:
1. **First:** Checks `config.yaml` for credentials
2. **Fallback:** If not in YAML, checks environment variables
3. **Error:** If neither exists, raises an error

This means you can:
- Use **only** `.env` (leave config.yaml with placeholders)
- Use **only** `config.yaml` (don't create .env)
- Use **both** (config.yaml takes precedence)

---

## Files That Are Gitignored (Safe)

✅ `.env` - Environment variables
✅ `config.yaml` - Configuration with credentials
✅ `.streamlit/secrets.toml` - Streamlit secrets (if used)

## Files That Are NOT Gitignored (Templates Only)

⚠️ `.env.template` - Template with placeholders
⚠️ `config.yaml.template` - Template with placeholders

**Never put real credentials in template files!**

---

## For Production Deployment

### Streamlit Cloud
Use Streamlit Secrets:
1. Go to app settings
2. Add secrets in TOML format:
   ```toml
   [snowflake]
   account = "your-account"
   user = "your_user"
   password = "your_password"
   warehouse = "COMPUTE_WH"
   database = "RAG_DB"
   schema = "PUBLIC"
   ```

### Docker/Kubernetes
Use environment variables:
```bash
docker run -e SNOWFLAKE_ACCOUNT=... -e SNOWFLAKE_USER=... app
```

### Snowpark Container Services
Use Snowflake secrets management

---

## Checking for Exposed Credentials

Before committing, always check:

```bash
# Check what will be committed
git status

# Make sure these are NOT listed:
# - .env
# - config.yaml
# - Any file with real credentials

# If you accidentally added them:
git reset HEAD .env
git reset HEAD config.yaml
```

---

## If You Accidentally Committed Credentials

1. **Immediately rotate/change your password** in Snowflake
2. Remove from git history:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config.yaml" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. Force push (if already pushed to remote)
4. **Change your Snowflake password again**

---

## Summary

✅ **DO:**
- Use `.env` or `config.yaml` for local development
- Keep credentials in gitignored files
- Use environment variables in production
- Rotate credentials regularly

❌ **DON'T:**
- Put credentials in template files
- Commit `.env` or `config.yaml`
- Share credentials in code or documentation
- Use the same password across environments

---

**Your credentials are now safe!** 🔒
