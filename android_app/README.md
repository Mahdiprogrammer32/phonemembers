# Virtual Contact Manager — Android Edition 📱

A professional Android application for managing virtual/group contacts, built with KivyMD and SQLite.

## Features

- 📱 Material Design dark-themed UI
- 🔢 Sequential number generation with preview
- 📥 Import contacts from TXT/CSV files in Downloads folder
- 📤 Export contacts to TXT/CSV
- 🗑 Safe deletion — only app-created contacts can be removed
- 📊 Real-time progress tracking
- 📋 Color-coded log panel
- 🔄 SQLite persistent storage

## Requirements

- Python 3.11+
- Linux (for Buildozer — use WSL2 on Windows)
- Android SDK + NDK (installed by Buildozer)

## Setup (Desktop Testing)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python main.py
```

## Build APK

### Prerequisites (Linux only)

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y \
    git zip unzip openjdk-17-jdk python3-pip autoconf \
    libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev

# Install Buildozer
pip install buildozer

# Install Cython
pip install cython
```

### Build

```bash
cd android_app

# Initialize (first time only)
buildozer init

# Build debug APK
buildozer android debug

# Build release APK
buildozer android release
```

The APK will be in `android_app/bin/`.

### Install on Device

```bash
# Via USB (device must be in developer mode)
buildozer android debug deploy run

# Or copy APK manually
adb install android_app/bin/vcm-1.0.0-debug.apk
```

## Project Structure

```
android_app/
├── main.py                 # Entry point
├── buildozer.spec          # Android build config
├── requirements.txt
├── README.md
└── app/
    ├── __init__.py
    ├── config/
    │   └── settings.py     # Android-aware config
    ├── database/
    │   ├── database.py     # SQLite layer
    │   └── models.py       # Data models
    ├── services/
    │   ├── number_generator.py
    │   ├── contact_service.py
    │   ├── import_service.py
    │   └── export_service.py
    ├── gui/
    │   └── main_app.py     # KivyMD UI
    └── utils/
        ├── phone.py        # Phone normalization
        ├── validators.py   # Input validation
        └── logger.py       # Logging
```

## Shared Code with Desktop

The core modules (`database/`, `services/`, `utils/`) are shared with the desktop (PySide6) version. Only the GUI layer differs:
- Desktop: PySide6 (Qt widgets)
- Android: KivyMD (Material Design)

## How It Works on Android

1. **Import**: Reads `.txt` / `.csv` files from your **Downloads** folder
2. **Export**: Saves files to your **Downloads** folder
3. **Storage**: App data (database, logs) is stored in internal storage
4. **Permissions**: Requires storage access for import/export

## License

MIT
