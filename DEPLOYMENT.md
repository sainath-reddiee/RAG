# Streamlit Cloud Deployment Guide

## 🚀 Deploying to Streamlit Cloud

### Step 1: Prepare Your Repository
1. Make sure all your code is committed to GitHub
2. Ensure `.streamlit/secrets.toml` is in `.gitignore` (already done)

### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your GitHub repository
4. Set main file path: `streamlit_app/app.py`
5. Click "Deploy"

### Step 3: Add Secrets
1. In your Streamlit Cloud dashboard, click on your app
2. Click "⚙️ Settings" → "Secrets"
3. Paste the following (fill in your actual values):

```toml
[snowflake]
account = "your-account-identifier"
user = "your-username"
password = "your-password"
warehouse = "your-warehouse"
database = "your-database"
schema = "your-schema"
role = "your-role"

[app]
top_k = 5
llm_model = "mistral-large2"
max_tokens = 2048
temperature = 0.7
max_file_size_mb = 10
allowed_extensions = ["txt", "pdf", "docx", "md"]
```

4. Click "Save"
5. Your app will automatically restart with the new secrets!

## 🔒 Security Notes

- ✅ Secrets are encrypted and never exposed in your code
- ✅ Only you can see the secrets in the Streamlit dashboard
- ✅ The app will work locally with `config.yaml` and on Streamlit Cloud with secrets
- ✅ Never commit `config.yaml` or `.streamlit/secrets.toml` to Git

## 📝 Local Development

For local development, continue using `config.yaml`:
1. Copy `config.yaml.template` to `config.yaml`
2. Fill in your credentials
3. Run: `streamlit run streamlit_app/app.py`

The code automatically detects if it's running on Streamlit Cloud and uses secrets, or locally and uses config.yaml!
