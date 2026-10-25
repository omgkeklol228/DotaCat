@echo off
chcp 65001 >nul
rem Запуск с консолью — видно ошибки, если что-то пошло не так
cd /d "%~dp0"
python -m dotacat
pause
