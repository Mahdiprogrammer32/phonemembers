# Virtual Contact Manager 📱

A professional desktop application for managing virtual/group contacts with a modern dark-themed GUI.

## Features

- **Number Generation** — Generate sequential phone numbers with customizable start, count, step, and name prefix
- **Phone Normalization** — Automatically converts various formats (`0912...`, `+98912...`, `0098912...`) to a standard format
- **Import/Export** — Support for both TXT and CSV file formats
- **Contact Tracking** — Each contact has a unique `internal_id`; only application-created contacts can be deleted
- **Safety First** — Original user contacts are never modified or deleted
- **Real-time Logging** — Color-coded log panel with INFO, SUCCESS, WARNING, and ERROR levels
- **Progress Tracking** — Live progress bar with Total/Processed/Success/Failed/Skipped statistics
- **Thread-safe Operations** — GUI never freezes during long operations
- **SQLite Database** — Persistent storage for contacts, operations, logs, and settings

## Requirements

- Python 3.11+
- PySide6
- python-dotenv

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd virtual-contact-manager

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

## Running the Application

```bash
python main.py
```

## Building an Executable (Windows)

```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller --onefile --windowed --name "VirtualContactManager" main.py

# The executable will be in the dist/ folder
```

## Project Structure

```
├── main.py                          # Entry point
├── requirements.txt                 # Dependencies
├── .env.example                     # Environment template
├── README.md
├── app/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # Application configuration
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py             # SQLite access layer
│   │   └── models.py               # Data models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── number_generator.py     # Sequential number generation
│   │   ├── contact_service.py      # Contact CRUD operations
│   │   ├── import_service.py       # TXT/CSV import
│   │   └── export_service.py       # TXT/CSV export
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py          # Main application window
│   │   ├── dialogs.py              # Confirmation & file dialogs
│   │   └── widgets.py              # Custom reusable widgets
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── phone.py                # Phone normalization
│   │   ├── validators.py           # Input validation
│   │   └── logger.py               # Application logger
│   └── tests/
│       ├── __init__.py
│       └── test_core.py            # Unit tests
```

## Running Tests

```bash
python -m pytest app/tests/ -v
# or
python -m unittest app.tests.test_core -v
```

## Usage

1. **Generate Numbers**: Fill in Start Number, Count, Name Prefix, and Step, then click **Preview** to see the numbers. Click **Generate** to create contacts in the database.

2. **Import**: Click **TXT** or **CSV** under Import to load contacts from a file.

3. **Export**: Click **TXT** or **CSV** under Export to save your contacts.

4. **Delete Created Contacts**: Removes only contacts created by this application. Your original contacts remain untouched.

5. **Delete Selected**: Select rows in the table and click **Delete Selected**.

## Safety

- Only contacts with `created_by_app = true` can be deleted by the application
- All destructive operations require user confirmation
- Credentials and tokens are never logged
- Sensitive configuration is stored in environment variables, not in source code

## License

MIT
# phonemembers
