The inspection has identified the first set of concrete problems. We can fix these without touching the audio engine yet.

## What I found

| Issue | Impact | Action |
|---|---|---|
| Missing root `README.md` | `pyproject.toml` references a file that doesn't exist | Restore it |
| Missing root `.gitignore` | Generated files can enter future commits | Create it |
| 20 tracked `.pyc` files | Compiled files are polluting source control | Remove them from Git tracking |
| Build workflow uses `main.py` | The new entry point is actually `src/main.py` | Correct the workflow |
| Build workflow expects root `requirements.txt` | Dependencies currently live elsewhere | Consolidate dependency management |

Your root `assets/` directory already contains the background and logo files. We will preserve those.

# Step 4 — Repair the repository foundation

We will make three changes first. These are safe and do not alter your application logic.

### 1. Create the root `.gitignore`

Run this in PowerShell:

```powershell
@'
# Python
__pycache__/
*.py[cod]
*.pyo

# Virtual environments
.venv/
venv/
env/

# Testing and tooling
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Build artifacts
build/
dist/
*.egg-info/

# IDE
.vscode/
.idea/

# Application data and local configuration
.env
*.db
*.sqlite
*.sqlite3

# OS
.DS_Store
Thumbs.db
'@ | Set-Content -Encoding utf8 .gitignore
```

This puts the ignore rules where Git expects them: at the repository root.

### 2. Restore the root README

Rather than copying the old README with its outdated architecture diagram, create a clean root README.

Run:

```powershell
@'
# Bragi

Bragi is a desktop application for fretboard mastery, instrument tuning, pitch detection, chord recognition, and ear training.

The project combines real-time audio analysis, music theory, interactive training exercises, and persistent practice analytics.

## Project Vision

Bragi is intended to support guitar, bass, and other stringed instruments through:

- Real-time chromatic tuning.
- Accurate monophonic pitch detection.
- Polyphonic chord recognition.
- Note, chord, scale, and arpeggio training.
- Ear training for intervals, chords, and inversions.
- Custom instrument profiles and alternate tunings.
- Practice statistics, progression, and achievements.

## Technology

- Python
- Flet
- NumPy and SciPy
- SoundDevice / PortAudio
- Pydantic
- SQLite
- PyInstaller

## Development Setup

Python 3.10 or newer is required.

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

Launch Bragi:

```powershell
python src/main.py
```

## Project Structure

```text
Bragi/
├── assets/
├── src/
│   ├── core/
│   ├── domain/
│   ├── dsp/
│   ├── storage/
│   └── ui/
├── tests/
├── AppRestructure/
├── .github/
└── pyproject.toml
```

`src/` contains the newer application architecture.

`AppRestructure/` is retained as a reference implementation while functionality is progressively integrated into the newer application.

## Development Principles

- Preserve the original Bragi feature vision.
- Keep audio capture separate from DSP processing.
- Keep the real-time audio callback lightweight.
- Separate audio analysis, evaluation, application state, and UI responsibilities.
- Validate DSP changes using synthetic signals and real instruments.
- Preserve existing user data and database compatibility.
- Test changes before integrating them into the application.

## License

Copyright © Arthur Belanger. All Rights Reserved.
'@ | Set-Content -Encoding utf8 README.md
```

### 3. Remove tracked Python cache files

This removes compiled files from Git's index but **does not delete your local source code or working files**.

Run:

```powershell
git rm -r --cached -- ':(glob)**/__pycache__/**'
```

If Git reports that no files matched, stop and tell me. Otherwise, continue.

### 4. Verify the changes

Run:

```powershell
git status --short
```

Then:

```powershell
git ls-files | Select-String "__pycache__|\.pyc$"
```

The second command should return no results.

---
