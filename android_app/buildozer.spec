[app]

# App info
title = Virtual Contact Manager
package.name = vcm
package.domain = com.vcm.app
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,db
version = 1.0.0

# Requirements
requirements = python3,pyside6,kivymd,sqlite3,android

# Python entry point
source.main = main.py

# Android settings
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 26
android.ndk = 25b
android.arch = arm64-v8a

# Build settings
android.release_artifact = apk
fullscreen = 0
orientation = portrait

# Presplash
# presplash.filename = %(source.dir)s/assets/presplash.png

# Icon
# icon.filename = %(source.dir)s/assets/icon.png

# Log level
log_level = 2

# Private storage for app data
android.private_storage = True

# Android gradle dependencies (for buildozer)
# android.gradle_dependencies =

# Android manifest
android.add_activites = org.kivy.android.PythonActivity

# P4A recipe
p4a.branch = develop

# Skip gradle dependencies check
android.skip_gradle = True

[buildozer]
warn_on_root = 0
