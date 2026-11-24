"""Entrada opcional: conserva la API del equipo y monta el contrato del frontend.

Terminal BACKEND (raíz): python -m uvicorn main_interfaz:app --reload --port 8000
Los archivos main.py y app/ permanecen sin modificaciones.
"""
from main import app
from integracion_frontend.aplicacion import app as api_interfaz

app.mount('/interfaz', api_interfaz, name='interfaz-gamefinder')
