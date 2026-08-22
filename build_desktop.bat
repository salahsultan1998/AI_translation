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

if exist ".env" (
    copy /Y ".env" "dist\LocaTool\.env" >nul
    echo Copied .env into dist\LocaTool\
) else (
    echo WARNING: no .env found in the project folder - the app will not
    echo be able to connect to Supabase or the AI models until you add one.
)

echo.
echo Done. The app is at dist\LocaTool\LocaTool.exe
pause
