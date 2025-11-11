from __future__ import annotations
import re, json
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from icalendar import Calendar as ICalCalendar, Event as ICalEvent

TZ_FALLBACK = "Europe/Madrid"

def read_clean_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw:
        raise ValueError(f"El archivo JSON '{path}' está vacío.")

    # Limpieza de fences/ruido comunes
    raw = (raw.lstrip("\ufeff")
              .replace("```json", "")
              .replace("```JSON", "")
              .replace("```", "")
              .replace("Claro,", "")
              .replace("Aquí tienes", ""))

    # Reemplaza dobles llaves por simples (por si el modelo las ha escapado)
    raw = raw.replace("{{", "{").replace("}}", "}")

    # Extrae el último bloque con llaves (por si el modelo antepone texto)
    m = re.search(r"\{.*\}\s*$", raw, re.DOTALL)
    if not m:
        raise ValueError(f"No se encontró un objeto JSON válido en {path}.\nPrimeras líneas:\n{raw[:300]}")
    cleaned = m.group(0)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ JSON inválido en {path}: {e}\nFragmento:\n{cleaned[:400]}")

def parse_local(dt: str, tzname: str) -> datetime:
    return datetime.fromisoformat(dt).replace(tzinfo=ZoneInfo(tzname))


def json_to_ics(json_path: Path, ics_path: Path, tz_fallback: str = TZ_FALLBACK) -> None:
    data = read_clean_json(json_path)
    tzname = data.get("calendar", {}).get("timezone", tz_fallback)
    prodid = data.get("calendar", {}).get("prodid", "-//Plan//GenAI//ES")

    cal = ICalCalendar()
    cal.add("prodid", prodid)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")


    now_utc = datetime.now(timezone.utc)


    for i, evj in enumerate(data.get("events", []), 1):
        for k in ("summary", "start", "end"):
            if k not in evj:
                raise ValueError(f"Evento #{i} sin '{k}'")
        ev = ICalEvent()
        ev.add("summary", evj["summary"])
        if evj.get("description"): ev.add("description", evj["description"])
        if evj.get("location"): ev.add("location", evj["location"])


        if evj.get("all_day", False):
            s = datetime.fromisoformat(evj["start"]).date()
            e = datetime.fromisoformat(evj["end"]).date()
            ev.add("dtstart", s); ev.add("dtend", e)
        else:
            dtstart = parse_local(evj["start"], tzname)
            dtend = parse_local(evj["end"], tzname)
            if dtend <= dtstart:
                raise ValueError(f"Evento #{i} tiene end <= start")
            ev.add("dtstart", dtstart); ev.add("dtend", dtend)

        ev.add("uid", f"uned-plan-{i}")
        ev.add("dtstamp", now_utc)
        if evj.get("rrule"): ev.add("rrule", evj["rrule"])
        cal.add_component(ev)

    ics_path.write_bytes(cal.to_ical())

def resolve_calendar(summary: str, calendars: dict[str, str]) -> tuple[str, str]:
    title = (summary or "").lower().strip()

    if "estudio" in title or "📚" in title:
        key = "ESTUDIOS"
    elif "trabajo" in title or "💼" in title:
        key = "TRABAJO"
    elif "rutina" in title or "🌀" in title:
        key = "RUTINAS"
    elif "mejora" in title or "⚙️" in title:
        key = "MEJORA"
    else:
        key = "DEFAULT"

    cal_id = calendars.get(key) or "primary"
    if not str(cal_id).strip():
        cal_id = "primary"
    # si cayó en primary pero no existe DEFAULT explícito, loguea como PRIMARY
    if cal_id == "primary" and key == "DEFAULT" and "DEFAULT" not in calendars:
        key = "PRIMARY"
    return key, cal_id
