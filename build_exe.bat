@echo off
chcp 65001 >nul
title Build EXE - Whisper Translation Tool
color 0B

echo ===================================================
echo     Whisper Translation Tool - EXE Builder
echo ===================================================
echo.

if not exist "venv\Scripts\pyinstaller.exe" (
    echo [INFO] Installiere PyInstaller...
    call venv\Scripts\pip.exe install pyinstaller
)

echo [INFO] Starte PyInstaller Build-Prozess...
echo.

:: PyInstaller ausfuehren
:: --noconfirm: Ueberschreibt alte Builds ohne zu fragen
:: --onedir: Erstellt einen Ordner mit der .exe und allen DLLs (besser fuer grosse KI-Modelle als --onefile)
:: --windowed / --noconsole: Versteckt das Konsolenfenster im Hintergrund
:: --icon: Setzt das Icon der .exe
:: --add-data: Fuegt zusaetzliche Dateien hinzu, die PyInstaller nicht automatisch findet

call venv\Scripts\pyinstaller.exe --noconfirm ^
--onedir ^
--windowed ^
--icon "icon.ico" ^
--add-data "icon.ico;." ^
--add-data "icon.png;." ^
--add-data "sounds;sounds" ^
app.py

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [FEHLER] Beim Erstellen der EXE ist ein Fehler aufgetreten.
    pause
    exit /b 1
)

echo.
color 0A
echo ===================================================
echo [ERFOLG] Die EXE wurde erfolgreich erstellt!
echo.
echo Du findest das fertige Programm im Unterordner:
echo "dist\app"
echo.
echo Dort liegt die Datei "app.exe" (oder "Whisper Translation Tool.exe", je nach Konfiguration).
echo Du kannst diesen gesamten Ordner als ZIP verpacken und verschicken!
echo ===================================================
pause
