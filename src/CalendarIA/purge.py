from __future__ import annotations
from pathlib import Path
from datetime import datetime, date, time, timezone
import time as _time
import random
from typing import Dict, Iterable, Optional, Tuple

from googleapiclient.errors import HttpError
from google_calendar import ensure_api_auth

SCOPES = ['https://www.googleapis.com/auth/calendar']


def _parse_since(since: str) -> datetime:
    """
    Acepta: YYYY-MM-DD  ó  YYYY-MM-DDTHH:MM:SSZ  ó  YYYY-MM-DDTHH:MM:SS±HH:MM
    Si viene solo fecha, asume 00:00:00Z (UTC).
    """
    s = since.strip()
    if "T" in s:
        # ISO completo; normaliza a UTC
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    # Solo fecha → medianoche UTC
    y, m, d = map(int, s.split("-"))
    return datetime.combine(date(y, m, d), time(0, 0, 0, tzinfo=timezone.utc))


def _iter_events_since(service, calendar_id: str, time_min_iso: str):
    next_page = None
    while True:
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min_iso,
            maxResults=2500,
            singleEvents=True,
            orderBy='startTime',
            pageToken=next_page
        ).execute()
        items = result.get('items', []) or []
        for it in items:
            yield it
        next_page = result.get('nextPageToken')
        if not next_page:
            break


def _should_delete(ev: dict, prefixes: Optional[Tuple[str, ...]]) -> bool:
    if not prefixes:
        return True
    summary = (ev.get('summary') or '')
    return any(summary.startswith(p) for p in prefixes)


def _delete_with_retries(service, calendar_id: str, event_id: str, max_retries: int = 6) -> bool:
    attempt = 0
    while True:
        try:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return True
        except HttpError as e:
            status = getattr(e, "status_code", None) or (e.resp.status if hasattr(e, "resp") else None)
            if status in (403, 429) and attempt < max_retries:
                attempt += 1
                sleep_s = min(64, 2 ** attempt) + random.uniform(0, 0.8)
                print(f"      ⏳ Rate limit ({status}). Reintento {attempt} en {sleep_s:.1f}s…")
                _time.sleep(sleep_s)
                continue
            else:
                print(f"      ❌ Error: {e}")
                return False
        except Exception as e:
            print(f"      ❌ Error: {e}")
            return False


def purge_events(
    calendars: Dict[str, str],
    since: str,
    *,
    prefixes: Optional[Iterable[str]] = None,
    dry_run: bool = True,
    client_secrets: Path = Path("secrets/calendar.json"),
    token_pickle: Path = Path("secrets/token.pickle"),
) -> None:
    """
    Borra eventos desde 'since' (UTC) en los calendarios indicados.
    - calendars: dict categoría→calendarId (o pasa {"PRIMARY":"primary"} para el principal)
    - since: ISO simple (YYYY-MM-DD) o ISO completo (…T…Z)
    - prefixes: iterable de prefijos de título; si se da, solo borra los que empiecen por alguno
    - dry_run: True = no borra, solo muestra
    """
    dt_since = _parse_since(since)
    time_min_iso = dt_since.isoformat().replace("+00:00", "Z")

    service = ensure_api_auth(client_secrets, token_pickle)

    print(f"⏳ Buscando y {'simulando borrado' if dry_run else 'borrando'} eventos desde {dt_since.date()} (UTC)")
    print("Calendarios destino:")
    for name, cal_id in calendars.items():
        print(f"— {name}: {cal_id}")

    total_borrados = 0
    total_errores = 0

    pref_tuple = tuple(prefixes) if prefixes else None

    for name, cal_id in calendars.items():
        print(f"\n📚 Calendario: {name}")
        # Listado
        events = list(_iter_events_since(service, cal_id, time_min_iso))
        print(f"   Encontrados {len(events)} eventos desde {dt_since.date()}.")

        # Vista previa (hasta 10)
        preview = 0
        for ev in events:
            if _should_delete(ev, pref_tuple):
                start = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date', ''))
                print(f"   - {start}  {ev.get('summary','(sin título)')}")
                preview += 1
                if preview >= 10:
                    break
        if len(events) - preview > 0:
            print(f"   ... y {len(events)-preview} más (no listados).")

        if dry_run:
            print("   🚫 DRY-RUN activo. No se borra nada.")
            continue

        print("   🚨 Borrando…")
        borrados = 0
        errores = 0
        for ev in events:
            if not _should_delete(ev, pref_tuple):
                continue
            ok = _delete_with_retries(service, cal_id, ev['id'])
            if ok:
                borrados += 1
            else:
                errores += 1
            _time.sleep(0.2 + random.uniform(0, 0.2))  # pacing

        print(f"   ✅ {borrados} eliminados, {errores} con error.")
        total_borrados += borrados
        total_errores += errores

    print(f"\n🏁 Resumen total: {total_borrados} borrados, {total_errores} con error(es).")
    if dry_run:
        print("👉 Ejecuta con --no-dry-run para borrar de verdad.")
