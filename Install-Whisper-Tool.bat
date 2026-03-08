@echo off
chcp 65001 >nul
color 0B
title Installation - Whisper Translation Tool

echo ===================================================
echo     Whisper Translation Tool - Installation
echo ===================================================
echo.

:: 1. Ueberpruefen, ob Python installiert ist
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [FEHLER] Python ist nicht installiert.
    echo Bitte lade dir Python herunter und installiere es: https://www.python.org/downloads/
    echo WICHTIG: Setze beim Installieren unbedingt das Haekchen bei "Add Python to PATH"!
    echo.
    pause
    exit /b 1
)

echo [OK] Python gefunden.
echo.

:: 2. Virtuelle Umgebung erstellen
if not exist "venv\" (
    echo [INFO] Erstelle virtuelle Umgebung (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        color 0C
        echo [FEHLER] Konnte virtuelle Umgebung nicht erstellen.
        pause
        exit /b 1
    )
    echo [OK] Virtuelle Umgebung erstellt.
) else (
    echo [INFO] Virtuelle Umgebung existiert bereits.
)
echo.

:: 3. Abhängigkeiten installieren
echo [INFO] Installiere benoetigte Pakete (das kann einen Moment dauern)...
call "venv\Scripts\python.exe" -m pip install --upgrade pip
call "venv\Scripts\python.exe" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    color 0C
    echo [FEHLER] Fehler bei der Installation.
    pause
    exit /b 1
)
echo [OK] Pakete erfolgreich installiert.
echo.

:: 4. Verknüpfung auf dem Desktop erstellen
echo [INFO] Erstelle Verknuepfung auf dem Desktop...
powershell -ExecutionPolicy Bypass -File "update_shortcut.ps1"
if %errorlevel% neq 0 (
    color 0E
    echo [WARNUNG] Verknuepfung konnte nicht automatisch erstellt werden.
) else (
    echo [OK] Verknuepfung auf dem Desktop erstellt!
)
echo.

echo ===================================================
echo Installation abgeschlossen! 
echo Du kannst das Tool nun ueber die Verknuepfung 
echo auf deinem Desktop starten.
echo ===================================================
pause
