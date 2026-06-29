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

    update_knockout()
    return 0


# Fechas de la fase eliminatoria (16avos en adelante). Generosas: 28 jun – 19 jul.
KO_DATES = [f"202606{d:02d}" for d in range(28, 31)] + [f"202607{d:02d}" for d in range(1, 20)]


def update_knockout():
    """Baja resultados reales de eliminatoria de ESPN y los guarda en knockout_data.json.

    SEGURO: solo agrega/actualiza partidos terminados; nunca borra uno guardado.
    Empareja por equipos (no por slot). Registra penales si ESPN los reporta.
    """
    kpath = os.path.join(WORKSPACE, "knockout_data.json")
    if not os.path.exists(kpath):
        return
    try:
        with open(kpath, encoding="utf-8") as f:
            ko = json.load(f)
    except Exception as e:
        print(f"  aviso: no se pudo leer knockout_data.json ({e})")
        return

    found = {}
    for d in KO_DATES:
        data = fetch(BASE + d)
        if not data:
            continue
        for ev in data.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            st = comp.get("status", {}).get("type", {})
            if not (st.get("completed") or st.get("name") == "STATUS_FULL_TIME"):
                continue
            home = away = None
            for c in comp.get("competitors", []):
                nm = esp((c.get("team") or {}).get("displayName", ""))
                try:
                    g = int(c.get("score"))
                except (TypeError, ValueError):
                    g = None
                try:
                    sh = int(c.get("shootoutScore"))
                except (TypeError, ValueError):
                    sh = None
                rec = {"name": nm, "g": g, "sh": sh}
                if c.get("homeAway") == "home":
                    home = rec
                elif c.get("homeAway") == "away":
                    away = rec
            if not home or not away or home["name"] is None or away["name"] is None:
                continue
            if home["g"] is None or away["g"] is None:
                continue
            pens = None
            if home["sh"] is not None and away["sh"] is not None:
                pens = [home["sh"], away["sh"]]
            key = frozenset((home["name"], away["name"]))
            found[key] = {
                "home": home["name"], "away": away["name"],
                "hg": home["g"], "ag": away["g"], "pens": pens,
                "date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
            }

    existing = {frozenset((m["home"], m["away"])): m for m in ko.get("real_matches", [])}
    before = len(existing)
    existing.update(found)
    ko["real_matches"] = sorted(existing.values(), key=lambda m: (m["date"], m["home"]))
    with open(kpath, "w", encoding="utf-8") as f:
        json.dump(ko, f, ensure_ascii=False, indent=2)
    nuevos = len(existing) - before
    for m in found.values():
        pen = f" (pen {m['pens'][0]}-{m['pens'][1]})" if m["pens"] else ""
        print(f"  ⚽ {m['home']} {m['hg']}-{m['ag']} {m['away']}{pen}")
    print(f"knockout: {len(found)} terminado(s) detectado(s), "
          f"{nuevos} nuevo(s); {len(ko['real_matches'])} guardados.")


if __name__ == "__main__":
    sys.exit(main())
