# Ariadne Health Agent - Project Structure & Guidelines

## 1. Directory Structure
We strictly separate **Code** (tracked by GitHub) from **Data** (local only, ignored).

```
Ariadne/
├── 00_Inbox/           # [DATA] Drop raw files here (Ignored by Git)
├── 01_Archive/         # [DATA] Processed files moved here (Ignored by Git)
├── 02_Database/        # [DATA] SQLite database (Ignored by Git)
├── 03_Apps/            # [CODE] Application source code (Tracked)
│   ├── agent.py        # Main Chat App
│   ├── ingest.py       # Data Processing Logic
│   └── setup_db.py     # Database Schema
├── 04_System/          # [CONFIG] System docs and maintenance scripts
│   ├── docs/           # Documentation
│   └── maintenance/    # Helpers (e.g., restore scripts)
├── .gitignore          # [CONFIG] Defines what to ignore
├── README.md           # [DOCS] Entry point for developers
├── requirements.txt    # [CONFIG] Python dependencies
└── START_APP.bat       # [EXE] Launcher for the user
```

## 2. GitHub Hygiene (What to Commit)

### ✅ DO COMMIT
- **Source Code**: Python files in `03_Apps`.
- **Configuration**: `requirements.txt`, `.gitignore`, `.bat` files.
- **Documentation**: `README.md` and files in `04_System/docs`.

### ⛔ DO NOT COMMIT (Already in .gitignore)
- **Personal Health Data**: contents of `00_Inbox` and `01_Archive`.
- **Database**: `*.db` files in `02_Database`.
- **Secrets**: `.streamlit/secrets.toml` or any `.env` files containing API Keys.
- **Virtual Env/Logs**: `__pycache__`, `*.log`.

## 3. Documentation Framework (DOE)

We follow a simplified **DOE (Definition, Operation, Engineering)** approach for documentation to keep it practical.

### D - Definition (The "What" & "Why")
- **Where**: `README.md`
- **Content**: High-level problem statement, workflow overview, and "How to Start".

### O - Operation (The "How-To")
- **Where**: `04_System/docs/Usage.md`
- **Content**: User Guide. How to add files, how to reset DB, how to interpret charts.

### E - Engineering (The "How It Works")
- **Where**: `04_System/docs/Architecture.md`
- **Content**: Technical details. Database schema, parser logic, function relations, deployment steps.

## 4. Maintenance Script Strategy
Move utility scripts (like `restore_archive.py`) to `04_System/maintenance` to keep the root clean. They are tools, not part of the core application flow.
