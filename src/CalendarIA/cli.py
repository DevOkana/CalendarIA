from __future__ import annotations
import argparse
from pathlib import Path
from config import Settings, ROOT
from prompt import render_prompt
from gemini_ia import GeminiClient
from ics_utils import json_to_ics
from routing import pick_calendar_id
import google_calendar as gcal
from purge import purge_events

def main():
    p = argparse.ArgumentParser(prog="uned-planner")
    p.add_argument("command", choices=["generate-json", "json-to-ics", "import-ics", "plan", "purge"], help="Acción a ejecutar")
    p.add_argument("--calendars", default=str(ROOT/"config/calendars.yaml"))
    p.add_argument("--schedule", default=str(ROOT/"config/schedule.yaml"))
    p.add_argument("--settings", default=str(ROOT/"config/settings.toml"))
    p.add_argument("--prompt", default=str(ROOT/"prompts/prompt_es.txt"))
    p.add_argument("--json-out", default=None)
    p.add_argument("--ics-out", default=None)

    # --- args específicos para purge ---
    p.add_argument("--since", help="Fecha/tiempo ISO para purga (UTC). Ej: 2025-11-04 o 2025-11-04T00:00:00Z")
    p.add_argument("--prefix", action="append",
                   help="Prefijo de título a filtrar (se puede repetir). Si no se da, borra todo.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", default=True,
                   help="Modo simulación (por defecto True).")
    p.add_argument("--no-dry-run", dest="dry_run", action="store_false",
                   help="Desactiva simulación: borra de verdad.")

    args = p.parse_args()

    conf = Settings(Path(args.calendars), Path(args.schedule), Path(args.settings))

    semana_inicio = conf.schedule["semana_inicio"]
    semana_final = conf.schedule["semana_final"]
    trabajo = conf.schedule["trabajo"]

    # Salidas
    name_out = conf.settings["output"]["base_name"]
    json_out = Path(args.json_out or conf.settings["output"]["json"]) \
    .with_name(f"{name_out}{semana_inicio}_{semana_final}.json")
    ics_out = Path(args.ics_out or conf.settings["output"]["ics"]) \
    .with_name(f"{name_out}{semana_inicio}_{semana_final}.ics")

    if args.command == "purge":
        if not args.since:
            raise SystemExit("❌ Debes indicar --since (YYYY-MM-DD o ISO completo).")
        # Usa los calendarios del YAML; si quieres filtrar, puedes pasar otro dict aquí
        purge_events(
            calendars=conf.calendars,
            since=args.since,
            prefixes=tuple(args.prefix) if args.prefix else None,
            dry_run=args.dry_run,
            client_secrets=conf.google_client_secrets,
        )
        return

    if args.command in ("generate-json", "plan"):
        prompt_text = render_prompt(Path(args.prompt), semana_inicio, semana_final, trabajo)
        #print(prompt_text)
        client = GeminiClient(conf.google_api_key, conf.settings["model"]["name"])
        json_out.write_text(client.generate_json(prompt_text), encoding="utf-8")
        print(f"✅ JSON generado: {json_out}")

    if args.command in ("json-to-ics", "plan"):
        json_to_ics(json_out, ics_out, conf.timezone)
        print(f"✅ ICS generado: {ics_out}")
    if args.command in ("import-ics", "plan"):
        gcal.import_ics_to_google(ics_out, conf.calendars, conf.timezone, pick_calendar_id, conf)


if __name__ == "__main__":
    main()