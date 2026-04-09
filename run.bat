@echo off
chcp 65001 > nul
cd /d "%~dp0"
python fetch_inventory.py
if errorlevel 1 (
  echo.
  echo [!] 실패. 로그 확인 후 엔터.
  pause
)
