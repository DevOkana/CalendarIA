from __future__ import annotations
from pathlib import Path
from datetime import date
from typing import Dict

_DIAS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

def _nombre_dia(fecha_iso: str) -> str:
    y, m, d = map(int, fecha_iso.split("-"))
    return _DIAS[date(y, m, d).weekday()]

def _normaliza_franja(franja: str) -> str:
    if franja.lower().strip() == "libranza":
        return "Libranza (sin trabajo)"
    fr = franja.replace(" ", "").replace("-", "–")
    return fr

def build_bloque_trabajo(trabajo: Dict[str, str]) -> str:
    parts = []
    for fecha, franja in sorted(trabajo.items()):
        parts.append(f" * {_nombre_dia(fecha)} {fecha}: {_normaliza_franja(franja)}")
    return "\n".join(parts)

def render_prompt(template_path: Path, semana_inicio: str, semana_final: str, trabajo: Dict[str, str]) -> str:
    tpl = template_path.read_text(encoding="utf-8")
    return (
    tpl
    .replace("{SEMANA_INICIO}", semana_inicio)
    .replace("{SEMANA_FINAL}", semana_final)
    .replace("{BLOQUE_TRABAJO}", build_bloque_trabajo(trabajo))
    )