@echo off
powershell.exe -ExecutionPolicy Bypass -File "%~dp0Encode-Video.ps1" -InputPath "%~1"
pause
