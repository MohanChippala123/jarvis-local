@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Python setup complete.
echo Install LM Studio from https://lmstudio.ai/download if needed.
echo Download a tool-capable local model and start its server on port 1234.
echo Then double-click Start Jarvis.cmd.
pause
exit /b 0
:fail
echo Setup failed. Review the error above.
pause
exit /b 1
