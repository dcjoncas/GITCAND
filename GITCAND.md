# GITCAND.md

## What this app is
GITCAND is a Flask-based GitHub candidate dashboard for DevReady.

It:
- searches GitHub public profiles using the GitHub API
- scores candidates based on stack fit, activity, and availability signals
- shows a selected candidate profile in a side panel
- generates a prefilled outreach email for the selected candidate
- uses DevReady green branding

## Main files
- `app.py` — main Flask app
- `Procfile` — Railway start command
- `requirements.txt` — Python dependencies
- `github_candidate_dashboard.html` — standalone themed reference file
- `github_candidate_miner.py` — related miner script
- `candidates.csv` — optional local CSV/reference data

## DevReady outreach text
The generated email says:

I am from DevReady and want to see if you are interested in joining our community and interviewing for a position we have open for you.

It also includes:
- `www.devready.io`
- `recruiting@devready.io`

## Local setup in VS Code

### Open terminal
```powershell
cd C:\GITCAND
```

### Activate environment
```powershell
.\venv_gitcand\Scripts\Activate.ps1
```

If blocked:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv_gitcand\Scripts\Activate.ps1
```

### Install dependencies
```powershell
python -m pip install flask requests gunicorn
pip freeze > requirements.txt
```

### Set token for current session
```powershell
$env:GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
```

### Run locally
```powershell
python .\app.py
```

Local URL:
```text
http://127.0.0.1:5000
```

## Procfile
Because the main file is now `app.py`, Procfile should be:

```text
web: gunicorn -b 0.0.0.0:$PORT app:app
```

## Git flow

### Normal save and push
```powershell
git add .
git commit -m "Update GITCAND"
git push origin main
```

### Force a fresh Railway redeploy if needed
```powershell
git commit --allow-empty -m "Force Railway redeploy"
git push origin main
```

## Railway deploy
1. Push code to GitHub repo `dcjoncas/GITCAND`
2. In Railway, deploy from GitHub repo
3. Add environment variable:
   - `GITHUB_TOKEN=YOUR_GITHUB_TOKEN_HERE`
4. Check Railway Start Command

Recommended start command:
```text
gunicorn -b 0.0.0.0:$PORT app:app
```

If Railway Start Command is blank, Procfile should handle it.

## DevReady styling
The updated interface uses:
- dark green/black background
- DevReady green accent buttons
- green profile cards
- selected candidate profile panel on the right

## What changed in the updated version
- candidate row selection
- selected candidate profile panel
- generate email button
- DevReady website and recruiting email added
- green DevReady theme

## Speed tips when working with me
You asked why some things feel slower and some faster. Usually the slower cases are when:
- I am reasoning through multiple conflicting setup issues
- deployment logs are inconsistent
- code, Git, and Railway all need to line up together

To speed things up:
- paste exact errors only, not paraphrases
- paste current file contents for `Procfile`, `requirements.txt`, and main app file
- say whether you want a quick fix or a full clean solution
- keep one current filename and one current deployment path
- ask for “exact commands only” when you want the shortest path

Best pattern:
- one request
- current files
- current error
- desired end state
