@echo off
title K-Tube Studio
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
start "" ".venv\Scripts\pythonw.exe" -m icontent ui --app %*
