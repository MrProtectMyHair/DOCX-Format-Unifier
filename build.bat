@echo off
echo ==========================================
echo  DOCX Format Unifier - Build Script
echo ==========================================
echo.
echo Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo Building executable...
pyinstaller --onefile --windowed --name "DOCX_Format_Unifier" main.py

echo.
echo Build complete!
echo Executable: dist\DOCX_Format_Unifier.exe
pause
