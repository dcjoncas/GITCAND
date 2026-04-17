# GITCAND

Canonical app file: `app.py`

## Added
- AI-powered JD parsing using the OpenAI API when `OPENAI_API_KEY` is set
- fallback heuristic JD parsing
- one-click `Add JD and Find Candidates`
- Postgres-ready tables and inserts when `DATABASE_URL` is set

## Required env vars
- `GITHUB_TOKEN`
- `OPENAI_API_KEY` optional but recommended
- `OPENAI_MODEL` optional
- `DATABASE_URL` optional

## Run
```powershell
cd C:\GITCAND
.\venv_gitcand\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
$env:OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"
python .\app.py
```

## Railway
```text
web: gunicorn -b 0.0.0.0:$PORT app:app
```
