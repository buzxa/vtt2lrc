@echo off
cd /d %~dp0
python src\vtt2lrc3.py "%~dp0\tar"
pause
