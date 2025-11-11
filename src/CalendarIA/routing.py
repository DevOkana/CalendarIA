from __future__ import annotations
import re
from typing import Dict

"""
* En caso de que el promt se cambie el nombre de los eventos se deberia de cambiar aqui tambien
* Los emojis son opcionales y se usan para facilitar la identificacion visual de los eventos
* Los eventos que no coincidan con ningun patron iran al calendario por defecto
"""
_PATTERNS = [
    (re.compile(r"^(💼\s*)?Trabajo$", re.I), "TRABAJO"),
    (re.compile(r"^(🚗\s*)?Preparación y desplazamiento al trabajo", re.I), "TRABAJO"),
    (re.compile(r"^(📚\s*)?Estudio\s*—\s*.+", re.I), "ESTUDIOS"),
    (re.compile(r"^(💻\s*)?Mejora profesional", re.I), "MEJORA"),
    (re.compile(r"^(🇬🇧\s*)?Inglés$", re.I), "MEJORA"),
    (re.compile(r"^(☕\s*)?Desayuno$", re.I), "RUTINAS"),
    (re.compile(r"^(🍝\s*)?Almuerzo$", re.I), "RUTINAS"),
    (re.compile(r"^(🍽️\s*)?Cena$", re.I), "RUTINAS"),
    (re.compile(r"^(🍎\s*)?Comer algo ligero$", re.I), "RUTINAS"),
    (re.compile(r"^(🧘‍♂️\s*)?Pausa activa$", re.I), "RUTINAS"),
    (re.compile(r"^(🥗\s*)?Pausa larga$", re.I), "RUTINAS"),
    (re.compile(r"^(😴\s*)?Descanso$", re.I), "RUTINAS"),
    (re.compile(r"^(😌\s*)?Descanso breve$", re.I), "RUTINAS"),
    (re.compile(r"^(🏃‍♂️\s*)?Ejercicio matutino$", re.I), "RUTINAS"),
    (re.compile(r"^(🌿\s*)?Bloque libre planificado$", re.I), "RUTINAS"),
]

def pick_calendar_id(summary: str, calendars: dict) -> str:
    """Devuelve el ID de calendario según el título o 'primary' por defecto."""
    # Siempre trabajar con texto
    title = (summary or "").lower().strip()

    # Mapear por categorías conocidas
    if "estudio" in title or "📚" in title:
        return calendars.get("ESTUDIOS", "primary")
    if "trabajo" in title or "💼" in title:
        return calendars.get("TRABAJO", "primary")
    if "rutina" in title or "🌀" in title:
        return calendars.get("RUTINAS", "primary")
    if "mejora" in title or "⚙️" in title:
        return calendars.get("MEJORA", "primary")

    # Fallback total
    return calendars.get("DEFAULT", "primary")



def pick_calendar_category(calendar_id: str, calendars: Dict[str, str]) -> str:
    for k, v in calendars.items():
        if v == calendar_id:
            return k
    return "DESCONOCIDO"