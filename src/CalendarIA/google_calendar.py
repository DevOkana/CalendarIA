from __future__ import annotations
import time, random
from pathlib import Path
from typing import Dict
from zoneinfo import ZoneInfo
from ics import Calendar as ICSCalendar
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import pickle

from config import Settings

SCOPES = ['https://www.googleapis.com/auth/calendar']


def ensure_api_auth(client_secrets: Path, token_pickle: Path) -> any:
    token_path = Path(token_pickle)
    creds = pickle.load(open(token_path, "rb")) if token_path.exists() else None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        pickle.dump(creds, open(token_path, "wb"))

    return build("calendar", "v3", credentials=creds)


def import_ics_to_google(ics_path: Path, calendars: Dict[str, str], timezone: str, pick_calendar_id, cfg: Settings) -> None:
    service = ensure_api_auth(Path(cfg.google_client_secrets), cfg.google_token_pickle)

    ics_text = Path(ics_path).read_text(encoding="utf-8")
    calendar = ICSCalendar(ics_text)
    events = list(calendar.events)

    z = ZoneInfo(timezone)
    base_interval = 1.0

    for ev in events:
        summary = ev.name or "(sin título)"
        dt_start = ev.begin.astimezone(z) if ev.begin.tzinfo else ev.begin.replace(tzinfo=z)
        dt_end   = ev.end.astimezone(z)   if ev.end.tzinfo   else ev.end.replace(tzinfo=z)

        body = {
            "summary": summary,
            "start": {"dateTime": dt_start.isoformat(), "timeZone": timezone},
            "end":   {"dateTime": dt_end.isoformat(),   "timeZone": timezone},
        }

        def _infer_cal_key(summary: str) -> str:
            t = (summary or "").lower()
            if "estudio" in t or "📚" in t:
                return "ESTUDIOS"
            if "trabajo" in t or "💼" in t:
                return "TRABAJO"
            if "rutina" in t or "🌀" in t:
                return "RUTINAS"
            if "mejora" in t or "⚙️" in t:
                return "MEJORA"
            return "DEFAULT"
        target_cal_id = pick_calendar_id(summary, calendars)


        if not target_cal_id or target_cal_id.strip() == "":
            target_cal_id = "primary"
        attempt = 0
        while True:
            try:
                # === solo para el print ===
                cal_key = _infer_cal_key(summary)
                mapped_id = (calendars or {}).get(cal_key, "")
                fell_to_primary = (not mapped_id or not str(mapped_id).strip())
                # si no inferimos nada y estás en primary: muestra PRIMARY
                display_key = (
                    f"{cal_key}{'→PRIMARY' if fell_to_primary else ''}"
                    if cal_key else ("PRIMARY" if target_cal_id == "primary" else "DESCONOCIDO")
                )
                # ==========================

                service.events().insert(calendarId=target_cal_id, body=body).execute()
                print(f"   ✔️ [{display_key}] {summary}")
                break
            except HttpError as e:
                status = getattr(e, "status_code", None) or (e.resp.status if hasattr(e, "resp") else None)
                if status in (403, 429) and attempt < 6:
                    attempt += 1
                    sleep_s = min(64, 2 ** attempt) + random.uniform(0, 0.8)
                    print(f"   ⏳ Rate limit ({status}). Reintento {attempt} en {sleep_s:.1f}s…")
                    time.sleep(sleep_s)
                else:
                    raise
            time.sleep(base_interval + random.uniform(0, 0.4))

    print("✅ Importación a Google Calendar completada.")