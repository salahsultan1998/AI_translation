@echo off
setlocal
cd /d "%~dp0"

echo Building LocaTool.exe ...
".ai_translation\Scripts\python.exe" -m PyInstaller --noconfirm --onedir --windowed --name LocaTool ^
  --collect-all streamlit ^
  --collect-all streamlit_cookies_controller ^
  --collect-all supabase ^
  --hidden-import excel_engine ^
  --hidden-import db_engine ^
  --hidden-import rag_engine ^
  --hidden-import agents ^
  --hidden-import custom_types ^
  --hidden-import openpyxl ^
  --hidden-import ahocorasick ^
  --hidden-import rapidfuzz ^
  --hidden-import pydantic ^
  --hidden-import dotenv ^
  --add-data "app.py;." ^
  --add-data "prompts.json;." ^
  desktop_app.py

echo.
echo Done. The app is at dist\LocaTool\LocaTool.exe
echo IMPORTANT: copy your .env file into dist\LocaTool\ (next to LocaTool.exe)
echo so the packaged app can connect to Supabase and the AI models.
pause
