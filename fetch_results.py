#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_results.py — Obtiene resultados reales del Mundial 2026 y actualiza fixtures.json.

Diseñado para correr en GitHub Actions (servidores de GitHub), donde la API pública
de ESPN responde en vivo. Sólo usa la librería estándar de Python.

Comportamiento SEGURO:
  - Sólo escribe el marcador de partidos que ESPN reporta como TERMINADOS.
  - Nunca borra ni "despublica" un resultado ya guardado.
  - Empareja por NOMBRE DE EQUIPO (no por número de partido).

Salida: actualiza fixtures.json en el mismo directorio. Devuelve código 0 siempre
que pueda leer/escribir el archivo (aunque no haya partidos nuevos).
"""
import json
import os
import sys
import time
import urllib.request

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates="
DATES = [f"202606{d:02d}" for d in range(11, 28)]  # 11–27 jun (fase de grupos)
WORKSPACE = os.path.dirname(os.path.abspath(__file__))

# ESPN (inglés)  ->  nombre en español usado en fixtures.json / quiniela_data.json
NAME_MAP = {
    "Mexico": "México", "South Africa": "Sudáfrica", "South Korea": "Corea del Sur",
    "Korea Republic": "Corea del Sur", "Czechia": "Rep. Checa", "Czech Republic": "Rep. Checa",
    "Canada": "Canadá", "Bosnia-Herzegovina": "Bosnia-Herz.", "Bosnia and Herzegovina": "Bosnia-Herz.",
    "Qatar": "Qatar", "Switzerland": "Suiza", "Brazil": "Brasil", "Morocco": "Marruecos",
    "Scotland": "Escocia", "Haiti": "Haití", "United States": "EE.UU.", "USA": "EE.UU.",
    "Paraguay": "Paraguay", "Australia": "Australia", "Türkiye": "Turquía", "Turkey": "Turquía",
    "Germany": "Alemania", "Curaçao": "Curazao", "Curacao": "Curazao",
    "Ivory Coast": "Costa de Marfil", "Côte d'Ivoire": "Costa de Marfil", "Ecuador": "Ecuador",
    "Netherlands": "Países Bajos", "Japan": "Japón", "Sweden": "Suecia", "Tunisia": "Túnez",
    "Belgium": "Bélgica", "Egypt": "Egipto", "Iran": "Irán", "IR Iran": "Irán",
    "New Zealand": "Nueva Zelanda", "Spain": "España", "Cape Verde": "Cabo Verde",
    "Cabo Verde": "Cabo Verde", "Saudi Arabia": "Arabia Saudita", "Uruguay": "Uruguay",
    "France": "Francia", "Senegal": "Senegal", "Norway": "Noruega", "Iraq": "Irak",
    "Argentina": "Argentina", "Algeria": "Argelia", "Austria": "Austria", "Jordan": "Jordania",
    "Portugal": "Portugal", "Congo DR": "RD del Congo", "DR Congo": "RD del Congo",
    "Uzbekistan": "Uzbekistán", "Colombia": "Colombia", "England": "Inglaterra",
    "Croatia": "Croacia", "Ghana": "Ghana", "Panama": "Panamá",
}


def esp(name):
    if name in NAME_MAP:
        return NAME_MAP[name]
    # normalización tolerante por si ESPN cambia algún string
    low = name.strip().lower()
    for k, v in NAME_MAP.items():
        if k.lower() == low:
            return v
    return None


def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 quiniela-bot"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"  aviso: fallo al leer {url[-8:]} ({e}); reintento {i+1}")
            time.sleep(2)
    return None


def main():
    fpath = os.path.join(WORKSPACE, "fixtures.json")
    with open(fpath, encoding="utf-8") as f:
        fixtures = json.load(f)

    # índice por conjunto de equipos -> fixture
    by_pair = {frozenset((fx["home"], fx["away"])): fx for fx in fixtures}

    finished = {}  # frozenset -> (teamA, goalsA, teamB, goalsB)
    for d in DATES:
        data = fetch(BASE + d)
        if not data:
            continue
        for ev in data.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            st = comp.get("status", {}).get("type", {})
            if not (st.get("completed") or st.get("name") == "STATUS_FULL_TIME"):
                continue
            teams = {}
            for c in comp.get("competitors", []):
                nm = esp((c.get("team") or {}).get("displayName", ""))
                try:
                    g = int(c.get("score"))
                except (TypeError, ValueError):
                    g = None
                if nm is not None and g is not None:
                    teams[c.get("homeAway")] = (nm, g)
            if "home" in teams and "away" in teams:
                key = frozenset((teams["home"][0], teams["away"][0]))
                finished[key] = teams

    changed = 0
    for key, teams in finished.items():
        fx = by_pair.get(key)
        if not fx:
            continue  # no es partido de fase de grupos en nuestro archivo
        h_name, h_goals = teams["home"]
        a_name, a_goals = teams["away"]
        # orientar a la orientación local/visitante de nuestro fixture
        if fx["home"] == h_name:
            hg, ag = h_goals, a_goals
        else:
            hg, ag = a_goals, h_goals
        if fx.get("homeGoals") != hg or fx.get("awayGoals") != ag or fx.get("status") != "FT":
            fx["homeGoals"], fx["awayGoals"], fx["status"] = hg, ag, "FT"
            changed += 1
            print(f"  ✔ {fx['home']} {hg}-{ag} {fx['away']} ({fx['group']})")

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=2)

    total_ft = sum(1 for fx in fixtures if fx["status"] == "FT")
    print(f"fetch_results: {changed} partido(s) actualizado(s). Terminados: {total_ft}/72.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
