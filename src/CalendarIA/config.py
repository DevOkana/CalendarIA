from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv
import tomllib
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

class Settings:
    def __init__(self,
                 calendars_path: Path,
                 schedule_path : Path,
                 settings_path: Path):
        self.timezone = os.getenv("TIMEZONE", "Europe/Madrid")
        self.lang = os.getenv("LANG", "es")
        self.google_api_key = os.getenv("GOOGLE_API_KEY", "")
        self.google_client_secrets = Path(os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "secrets/calendar.json"))
        self.google_token_pickle = Path(os.getenv("GOOGLE_TOKEN_PICKLE_FILE", "secrets/token.pickle"))

        self.calendars = self._read_yaml(calendars_path)
        self.schedule = self._read_yaml(schedule_path)
        self.settings = self._read_toml(settings_path)

    @staticmethod
    def _read_yaml(p: Path) -> Dict[str, Any]:
        with open(p, "r", encoding="utf-8") as fh:
            try:
                return yaml.safe_load(fh) or {}
            except yaml.parser.ParserError as e:
                raise ValueError(f"Error en el parseo del archivo YAML {p}: {e}. Por favor de revisar")

    @staticmethod
    def _read_toml(p: Path) -> Dict[str, Any]:
        with open(p, "rb") as fh:
            return tomllib.load(fh)

