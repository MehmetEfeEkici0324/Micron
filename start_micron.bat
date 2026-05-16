@echo off
echo MICRON baslatiliyor...
cd /d "c:\Users\MDH\Desktop\Micron\micron"
start "Ollama" /min ollama serve
timeout /t 2 /nobreak > nul
start "MICRON Server" c:\Python313\python.exe server.py
timeout /t 2 /nobreak > nul
start http://localhost:5000
echo MICRON hazir!
pause
