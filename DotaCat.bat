@echo off
chcp 65001 >nul
rem Запуск DotaCat без окна консоли
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw -m dotacat
  exit /b
)
where pyw >nul 2>nul
if %errorlevel%==0 (
  start "" pyw -3 -m dotacat
  exit /b
)
echo Python 3 не найден. Установите его с https://www.python.org/downloads/
pause
