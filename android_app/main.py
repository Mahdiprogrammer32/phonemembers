"""Android entry point — launches the KivyMD application."""

from __future__ import annotations

import os
import sys

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.gui.main_app import VCMApp

if __name__ == "__main__":
    VCMApp().run()
