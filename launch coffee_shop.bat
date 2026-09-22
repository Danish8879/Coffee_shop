@echo off
rem Start the coffee shop development server using the project virtual environment.
cd /d "%~dp0"
call .venv\Scripts\activate
python manage.py runserver
