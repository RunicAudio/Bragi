# Bragi

**A Guitar Learning, Pitch Detection, and Music Theory Training Application**

Bragi is a desktop music-learning application designed to help musicians develop pitch recognition, chord identification, fretboard knowledge, and overall musical understanding through interactive exercises and real-time audio analysis.

Built with Python, Flet, NumPy, and SQLite, Bragi combines real-time audio processing with an interactive training environment and persistent user progression.

---

## Features

### 1. Real-Time Pitch Detection

Bragi analyzes incoming audio signals to identify individual musical notes.

Current capabilities include:

- Real-time monophonic pitch detection.
- Frequency-to-note conversion.
- Note identification.
- Cents deviation measurement.
- RMS-based signal monitoring.
- Support for external audio interfaces.
- Configurable audio input devices.

The pitch detection system uses autocorrelation and peak interpolation to estimate fundamental frequencies.

### 2. Chord Detection

Bragi includes a polyphonic analysis system designed to identify multiple simultaneous musical notes.

Current capabilities include:

- FFT-based spectral analysis.
- Pitch-class detection.
- Chromagram analysis.
- Harmonic suppression.
- Multi-frame spectral integration.
- Chord recognition through detected pitch classes.

The chord detection system is designed to work alongside the monophonic pitch tracker without interfering with its processing.

### 3. Interactive Guitar Trainer

The Trainer provides an interactive environment for practicing note and chord identification using a connected instrument.

Current training modes include:

- Single Note Identification.
- Strummed Chord Identification.
- Arpeggio Chord Identification.

Training progress is recorded and connected to the application's progression system.

### 4. Ear Training

The Ear Training module provides listening exercises designed to improve musical recognition.

Current exercise modes include:

- Single Pitch Identification.
- Chord Quality Identification.

Audio samples are generated and played through the application's sample playback system.

### 5. Tuner

Bragi includes a real-time tuner interface displaying detected pitch information and tuning deviation.

### 6. Analytics and Progression

Bragi includes a gamification and analytics system designed to track learning progress.

Current functionality includes:

- Experience point accumulation.
- User levels.
- Consecutive correct-answer tracking.
- Practice attempt logging.
- Accuracy statistics.
- Response-time tracking.
- Achievement badges.
- Hero Boss progression tracking.

User progression and practice information are stored locally using SQLite.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Primary programming language |
| Flet | Desktop application interface |
| NumPy | Numerical processing and signal analysis |
| SciPy | Signal processing utilities |
| SoundDevice | Audio input and output |
| SoundFile | Audio file handling |
| SQLite | Local database and persistence |
| Pydantic | Data models and validation |
| PyInstaller | Application packaging |

Additional dependencies are defined in `pyproject.toml`.

---

## Project Structure

```text
Bragi/
│
├── src/
│   │
│   ├── main.py
│   │
│   ├── core/
│   │   └── app_state.py
│   │
│   ├── domain/
│   │   ├── chord_definitions.py
│   │   ├── gamification_policy.py
│   │   ├── music_theory.py
│   │   └── scale_definitions.py
│   │
│   ├── dsp/
│   │   ├── audio_engine.py
│   │   ├── chromagram.py
│   │   ├── pitch_tracker.py
│   │   └── sample_player.py
│   │
│   ├── storage/
│   │   ├── db_manager.py
│   │   └── path_utils.py
│   │
│   └── ui/
│       ├── app_shell.py
│       │
│       ├── components/
│       │   ├── header_nav.py
│       │   └── modals/
│       │
│       └── views/
│           ├── analytics_view.py
│           ├── ear_training_view.py
│           ├── trainer_view.py
│           └── tuner_view.py
│
├── assets/
│
├── pyproject.toml
│
├── .gitignore
│
└── README.md
```

*The structure above represents the primary application architecture. Additional files and resources may exist within individual directories.*

---

## Installation

### Requirements

- Windows 10/11 or another supported desktop operating system.
- Python 3.11 or newer.
- A working audio input device.
- Git (recommended for development).

### 1. Clone the Repository

```bash
git clone https://github.com/RunicAudio/Bragi.git
```

### 2. Navigate to the Project

```bash
cd Bragi
```

### 3. Create a Virtual Environment

Windows:

```powershell
python -m venv .venv
```

### 4. Activate the Environment

```powershell
.venv\Scripts\Activate.ps1
```

### 5. Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -e .
```

### 6. Launch Bragi

```powershell
python src/main.py
```

---

## Audio Configuration

Bragi uses SoundDevice for audio acquisition and processing.

For the best experience:

1. Connect your guitar or instrument to an audio interface.
2. Connect the interface to your computer.
3. Launch Bragi.
4. Open the device configuration interface.
5. Select the appropriate audio input.
6. Verify that incoming audio is being detected.

### Recommended Audio Configuration

| Setting | Recommendation |
|---|---|
| Sample Rate | 48,000 Hz |
| Input | Audio interface instrument input |
| Input Signal | Clean, unclipped signal |
| Monitoring | Direct monitoring or external monitoring |
| Instrument | Electric guitar, acoustic guitar, or compatible audio source |

Audio device availability and supported configurations depend on the operating system and hardware.

---

## Application Architecture

Bragi uses a modular architecture to separate audio processing, musical interpretation, application state, persistence, and interface rendering.

### Audio Processing Pipeline

```text
Audio Input
    |
    v
SoundDevice / PortAudio
    |
    v
Audio Capture Callback
    |
    v
Audio Processing Queue
    |
    v
Background DSP Worker
    |
    +----------------------+
    |                      |
    v                      v
Pitch Tracker        Chromagram Analyzer
    |                      |
    v                      v
Note Detection       Pitch-Class Detection
    |                      |
    +----------+-----------+
               |
               v
           AppState
               |
               v
          Flet Interface
```

### Architectural Components

**Core**

Manages centralized application state, event notifications, trainer configuration, and progression.

**Domain**

Contains music theory definitions, chord structures, scale definitions, and gamification rules.

**DSP**

Handles audio capture, pitch tracking, chromagram analysis, and sample playback.

**Storage**

Manages SQLite database operations and application data paths.

**UI**

Contains the Flet application shell, reusable interface components, modals, and individual application views.

---

## Data Storage

Bragi uses SQLite for local persistence.

Stored information includes:

- User progression.
- Experience points.
- User levels.
- Practice attempts.
- Response times.
- Accuracy statistics.
- Achievement unlocks.
- Hero Boss progression.

Application data is stored locally rather than requiring a remote database service.

---

## Development

The `dev` branch is the primary development branch.

The `main` branch is reserved for stable releases.

### Branch Workflow

```text
main
  |
  +-------------------
                      |
                     dev
                      |
              Feature Development
                      |
                Testing & Review
                      |
               Stable Integration
                      |
                     main
```

### Development Guidelines

- Keep DSP processing independent of UI rendering.
- Avoid placing audio-processing operations inside UI callbacks.
- Keep music theory calculations within the domain layer.
- Keep database operations within the storage layer.
- Use AppState for centralized application state.
- Prefer reusable UI components.
- Test changes before merging into the stable branch.
- Avoid committing generated build artifacts, local databases, or virtual environments.

---

## Current Development Status

Bragi is actively under development.

| Component | Status |
|---|---|
| Application Framework | Implemented |
| Audio Input | Implemented |
| Audio Device Selection | Implemented |
| Single-Note Detection | Implemented |
| Chord Detection | Implemented |
| Guitar Trainer | Implemented |
| Ear Training | Initial Implementation |
| Tuner | Implemented |
| Music Theory Foundation | Implemented |
| SQLite Persistence | Implemented |
| Analytics Dashboard | Initial Implementation |
| Gamification System | Initial Implementation |
| Automated Testing | Planned |
| Performance Optimization | Planned |
| Application Packaging | In Development |

Feature status reflects implementation, not comprehensive validation across all hardware and operating systems.

---

## Roadmap

Planned development priorities include:

- Automated unit and integration testing.
- Improved pitch detection accuracy and reliability.
- Improved polyphonic chord recognition.
- More advanced chord identification.
- Fretboard position recognition.
- Improved ear training exercises.
- Expanded music theory exercises.
- More comprehensive analytics.
- Expanded achievement and progression systems.
- Performance optimization.
- Improved application packaging and distribution.

---

## Contributing

Bragi is currently undergoing active development.

Contributions, suggestions, and bug reports are welcome.

When contributing:

1. Work from the latest `dev` branch.
2. Create a separate branch for significant features.
3. Keep changes modular.
4. Avoid introducing unnecessary dependencies.
5. Validate changes before submitting them for integration.

---

## License

License information will be added when the project's distribution and licensing terms are finalized.

---

**Bragi — Learn the Notes. Understand the Music. Master the Instrument.**
