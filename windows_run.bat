@echo off
REM ===========================================================
REM  P2P File Sharing Demo Launcher (Windows - Multi-Machine Ready)
REM ===========================================================

echo ===========================================================
echo   P2P FILE SHARING DEMO - MULTI MACHINE MODE
echo ===========================================================

set /p ROLE="Enter role (tracker / peerA / peerB): "

set PROJECT_DIR=%~dp0
set PYTHON_EXE=python
set TRACKER_PORT=9000
set PEER_A_PORT=5001
set PEER_B_PORT=5002

if /I "%ROLE%" NEQ "tracker" (
    set /p TRACKER_IP="Enter Tracker IP (e.g., 192.168.10.12): "
)

if /I "%ROLE%"=="tracker" (
    echo Starting TRACKER server...
    if not exist "%PROJECT_DIR%sample_files" (
        mkdir "%PROJECT_DIR%sample_files"
        echo This is Peer A sample file > "%PROJECT_DIR%sample_files\fileA.txt"
    )
    start "Tracker" cmd /k "%PYTHON_EXE% tracker.py"
    pause
    exit /b
)

if /I "%ROLE%"=="peera" (
    echo Starting PEER A...
    if not exist "%PROJECT_DIR%sample_files" (
        mkdir "%PROJECT_DIR%sample_files"
        echo This is Peer A sample file > "%PROJECT_DIR%sample_files\fileA.txt"
    )
    start "Peer A" cmd /k "%PYTHON_EXE% peer.py --peer-id PeerA --port %PEER_A_PORT% --shared-dir sample_files --tracker %TRACKER_IP%:%TRACKER_PORT%"
    pause
    exit /b
)

if /I "%ROLE%"=="peerb" (
    echo Starting PEER B...
    if not exist "%PROJECT_DIR%sample_files_b" (
        mkdir "%PROJECT_DIR%sample_files_b"
        echo This is Peer B sample file > "%PROJECT_DIR%sample_files_b\fileB.txt"
    )
    start "Peer B" cmd /k "%PYTHON_EXE% peer.py --peer-id PeerB --port %PEER_B_PORT% --shared-dir sample_files_b --tracker %TRACKER_IP%:%TRACKER_PORT%"
    pause
    exit /b
)

echo Invalid role. Use: tracker / peerA / peerB
pause
