#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_site.py — Genera index.html de la Quiniela Mundial 2026.

Fuentes:
  - quiniela_data.json : predicciones de cada participante (no se modifica)
  - fixtures.json      : calendario maestro oficial + resultados reales

Diseño robusto: los resultados se emparejan con las predicciones POR EQUIPOS
(no por número de partido), usando el conjunto {local, visitante} dentro de cada
grupo. Así nunca se asigna un resultado al partido equivocado.

Reglas de puntuación:
  +1 acertar ganador o empate
  +1 acertar goles del local
  +1 acertar goles del visitante
  (máximo 3 por partido)
Desempate: 1) más marcadores exactos  2) más cercano al total real de goles.

Uso:  python3 build_site.py
"""
import json
import os
from datetime import datetime

PLAYERS = ["Adam", "Diego", "Fer", "Santiago"]
WORKSPACE = os.path.dirname(os.path.abspath(__file__))

MESES = {
    "01": "ene", "02": "feb", "03": "mar", "04": "abr", "05": "may", "06": "jun",
    "07": "jul", "08": "ago", "09": "sep", "10": "oct", "11": "nov", "12": "dic",
}


def fecha_corta(iso):
    try:
        y, m, d = iso.split("-")
        return f"{int(d)} {MESES[m]}"
    except Exception:
        return iso


def winner(hg, ag):
    if hg is None or ag is None:
        return None
    if hg > ag:
        return "H"
    if ag > hg:
        return "A"
    return "D"


def points_for(p_home, p_away, hg, ag):
    """Devuelve (puntos, exacto_bool, etiquetas)."""
    if None in (p_home, p_away, hg, ag):
        return 0, False, []
    pts, tags = 0, []
    if winner(p_home, p_away) == winner(hg, ag):
        pts += 1; tags.append("Resultado")
    if p_home == hg:
        pts += 1; tags.append("Local")
    if p_away == ag:
        pts += 1; tags.append("Visitante")
    exacto = (p_home == hg and p_away == ag)
    return pts, exacto, tags


def load_json(name):
    with open(os.path.join(WORKSPACE, name), "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_optional(name):
    """Carga un JSON si existe; si no, devuelve None (para no romper el build)."""
    path = os.path.join(WORKSPACE, name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  No se pudo leer {name}: {e}")
        return None


# ===========================================================================
#  FASE ELIMINATORIA (bracket)
# ===========================================================================
FLAGS = {
    "Alemania": "🇩🇪", "Paraguay": "🇵🇾", "Francia": "🇫🇷", "Suecia": "🇸🇪",
    "Sudáfrica": "🇿🇦", "Canadá": "🇨🇦", "Países Bajos": "🇳🇱", "Marruecos": "🇲🇦",
    "Portugal": "🇵🇹", "Croacia": "🇭🇷", "España": "🇪🇸", "Austria": "🇦🇹",
    "EE.UU.": "🇺🇸", "Bosnia-Herz.": "🇧🇦", "Bélgica": "🇧🇪", "Senegal": "🇸🇳",
    "Brasil": "🇧🇷", "Japón": "🇯🇵", "Costa de Marfil": "🇨🇮", "Noruega": "🇳🇴",
    "México": "🇲🇽", "Ecuador": "🇪🇨", "Inglaterra": "🏴", "RD del Congo": "🇨🇩",
    "Argentina": "🇦🇷", "Cabo Verde": "🇨🇻", "Australia": "🇦🇺", "Egipto": "🇪🇬",
    "Suiza": "🇨🇭", "Argelia": "🇩🇿", "Colombia": "🇨🇴", "Ghana": "🇬🇭",
    "Arabia Saudita": "🇸🇦", "Corea del Sur": "🇰🇷", "Curazao": "🇨🇼", "Escocia": "🏴",
    "Haití": "🇭🇹", "Irak": "🇮🇶", "Irán": "🇮🇷", "Jordania": "🇯🇴",
    "Nueva Zelanda": "🇳🇿", "Panamá": "🇵🇦", "Qatar": "🇶🇦", "Rep. Checa": "🇨🇿",
    "Túnez": "🇹🇳", "Turquía": "🇹🇷", "Uruguay": "🇺🇾", "Uzbekistán": "🇺🇿",
}


def flag(team):
    return FLAGS.get(team, "🏳️")


def loser_of(match):
    return match["home"] if match["winner"] == match["away"] else match["away"]


def advancers(bracket):
    """Equipos que el jugador predice que AVANZAN a cada ronda."""
    return {
        "r16": [x["winner"] for x in bracket["r32"]],
        "qf": [x["winner"] for x in bracket["r16"]],
        "sf": [x["winner"] for x in bracket["qf"]],
        "final": [x["winner"] for x in bracket["sf"]],
        "campeon": bracket["final"]["winner"],
        "third": bracket["third"]["winner"],
    }


def score_knockout(bracket, real, points):
    """Puntos por acertar qué equipos llegan a cada ronda. real puede estar vacío."""
    adv = advancers(bracket)
    pts, detail = 0, {}
    for rnd in ("r16", "qf", "sf", "final"):
        real_set = set(real.get(rnd) or [])
        hits = sum(1 for t in adv[rnd] if t in real_set)
        gained = hits * points.get(rnd, 0)
        detail[rnd] = (hits, gained)
        pts += gained
    if real.get("campeon") and adv["campeon"] == real["campeon"]:
        pts += points.get("campeon", 0)
        detail["campeon"] = (1, points.get("campeon", 0))
    if real.get("third") and adv["third"] == real["third"]:
        pts += points.get("third", 0)
        detail["third"] = (1, points.get("third", 0))
    return pts, detail


def ko_pair_index(bracket):
    """frozenset(equipos) -> partido predicho (todas las rondas del bracket)."""
    idx = {}
    for r in ("r32", "r16", "qf", "sf"):
        for mt in bracket.get(r, []):
            idx[frozenset((mt["home"], mt["away"]))] = mt
    for single in ("final", "third"):
        mt = bracket.get(single)
        if mt:
            idx[frozenset((mt["home"], mt["away"]))] = mt
    return idx


def score_ko_player(bracket, real_matches):
    """Puntúa la eliminatoria igual que grupos (+1/+1/+1), emparejando por equipos.

    Devuelve totales y el detalle por par {frozenset: {pts, exact}} para anotar el bracket.
    """
    idx = ko_pair_index(bracket)
    pts = exact = played = 0
    per_pair = {}
    for rm in real_matches:
        key = frozenset((rm["home"], rm["away"]))
        mt = idx.get(key)
        if not mt:
            continue  # el jugador no predijo este cruce
        # orientar la predicción a la orientación local/visitante del partido real
        if mt["home"] == rm["home"]:
            ph, pa = mt["hg"], mt["ag"]
        else:
            ph, pa = mt["ag"], mt["hg"]
        p, ex, _ = points_for(ph, pa, rm["hg"], rm["ag"])
        pts += p
        played += 1
        if ex:
            exact += 1
        per_pair[key] = {"pts": p, "exact": ex}
    return {"pts": pts, "exact": exact, "played": played, "per_pair": per_pair}


def _kmatch_card(mt, real_index=None, detail=None):
    """Tarjeta de un partido de bracket. Si hay resultado real del cruce, lo anota."""
    if not mt:
        return ""
    h, a = mt["home"], mt["away"]
    hg, ag = mt["hg"], mt["ag"]
    win = mt["winner"]
    pen = ""
    if mt.get("pens"):
        pen = f'<div class="kpen">penales {mt["pens"][0]}-{mt["pens"][1]}</div>'
    rh = "krow win" if win == h else "krow"
    ra = "krow win" if win == a else "krow"

    rb = ""
    if real_index is not None:
        rm = real_index.get(frozenset((h, a)))
        if rm:
            if rm["home"] == h:
                rhg, rag, pp = rm["hg"], rm["ag"], rm.get("pens")
            else:
                rhg, rag = rm["ag"], rm["hg"]
                pp = list(reversed(rm["pens"])) if rm.get("pens") else None
            rpen = f' · pen {pp[0]}-{pp[1]}' if pp else ""
            d = (detail or {}).get(frozenset((h, a)))
            badge = ""
            if d is not None:
                if d["exact"]:
                    badge = '<span class="kb ex">+3 ✓</span>'
                elif d["pts"] > 0:
                    badge = f'<span class="kb pa">+{d["pts"]}</span>'
                else:
                    badge = '<span class="kb ze">0</span>'
            rb = f'<div class="kreal">real {rhg}-{rag}{rpen} {badge}</div>'

    return (
        f'<div class="kmatch">'
        f'<div class="{rh}"><span class="kt">{flag(h)} {h}</span><span class="kg">{hg}</span></div>'
        f'<div class="{ra}"><span class="kt">{flag(a)} {a}</span><span class="kg">{ag}</span></div>'
        f'{pen}{rb}</div>'
    )


def _kcolumn(title, matches, real_index=None, detail=None):
    cards = "".join(_kmatch_card(m, real_index, detail) for m in matches)
    return f'<div class="kcol"><div class="kcol-h">{title}</div>{cards}</div>'


def render_player_bracket(player, bracket, real_index=None, detail=None,
                          ko_pts=0, ko_played=0):
    champ = bracket["campeon"]
    fin = bracket["final"]
    runner = loser_of(fin)
    third = bracket["third"]["winner"]
    podium = (f'🥇 {flag(champ)} {champ} · 🥈 {flag(runner)} {runner} · '
              f'🥉 {flag(third)} {third}')
    cols = (
        _kcolumn("16avos", bracket["r32"], real_index, detail)
        + _kcolumn("Octavos", bracket["r16"], real_index, detail)
        + _kcolumn("Cuartos", bracket["qf"], real_index, detail)
        + _kcolumn("Semis", bracket["sf"], real_index, detail)
        + _kcolumn("Final", [bracket["final"]], real_index, detail)
        + _kcolumn("3er lugar", [bracket["third"]], real_index, detail)
    )
    subtotal = ""
    if ko_played:
        subtotal = (f'<span class="ko-sub">🏅 {ko_pts} pts de eliminatoria '
                    f'· {ko_played} jugado(s)</span>')
    return f"""
    <div class="ko-player">
      <div class="ko-head">
        <span class="ko-name">{player}</span>
        <span class="ko-podium">{podium}</span>
        {subtotal}
      </div>
      <div class="bracketwrap"><div class="bracket">{cols}</div></div>
    </div>"""


KO_CSS = """
<style>
.ko-rules{background:#eef3f8;border-left:4px solid #1b3a5b;padding:10px 14px;border-radius:0 8px 8px 0;font-size:.86rem;margin-bottom:14px}
.ko-player{border:1px solid #e6ebf1;border-radius:12px;padding:12px;margin-bottom:14px;background:#fff}
.ko-head{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:10px}
.ko-name{font-weight:800;color:#0d1b2a;font-size:1.1rem}
.ko-podium{background:#fff8e6;border:1px solid #c7ae4a;border-radius:20px;padding:3px 12px;font-size:.85rem;font-weight:600}
.ko-sub{background:#e7f6ec;border:1px solid #1a7d3c;color:#1a7d3c;border-radius:20px;padding:3px 12px;font-size:.85rem;font-weight:700}
.kreal{font-size:.68rem;text-align:center;background:#f2f5f9;color:#42525f;padding:2px 4px;border-top:1px solid #e6ebf1}
.kb{font-weight:800;border-radius:4px;padding:0 4px;margin-left:3px}
.kb.ex{background:#1a7d3c;color:#fff}
.kb.pa{background:#d7eede;color:#1a7d3c}
.kb.ze{background:#fde8e8;color:#9b2226}
.bracketwrap{overflow-x:auto;padding-bottom:6px}
.bracket{display:flex;gap:10px;min-width:max-content}
.kcol{display:flex;flex-direction:column;justify-content:space-around;gap:8px;min-width:148px}
.kcol-h{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#1b3a5b;text-align:center;background:#eef3f8;border-radius:6px;padding:3px 0}
.kmatch{border:1px solid #e6ebf1;border-radius:8px;overflow:hidden;font-size:.8rem}
.krow{display:flex;justify-content:space-between;align-items:center;padding:5px 8px;gap:6px;background:#fff;color:#7a8794}
.krow.win{background:#e7f6ec;color:#0d1b2a;font-weight:700}
.krow .kt{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.krow .kg{font-weight:800;color:#1a7d3c}
.kpen{font-size:.68rem;color:#9b2226;text-align:center;background:#fdf0f0;padding:2px}
.ko-pending{color:#8693a0;font-size:.88rem;background:#f7f9fb;border:1px dashed #cbd3db;border-radius:10px;padding:12px;text-align:center}
</style>"""


def render_knockout(knockout, scores=None):
    """Sección 'Fase Eliminatoria'. Devuelve '' si no hay datos (no rompe el build)."""
    if not knockout or not knockout.get("players"):
        return ""
    players = knockout["players"]
    scores = scores or {}
    real_matches = knockout.get("real_matches", []) or []
    real_index = {frozenset((m["home"], m["away"])): m for m in real_matches}
    n = len(real_matches)
    jugados = (f' Hasta ahora se han jugado <b>{n}</b> partido(s) de eliminatoria.'
               if n else ' Aún no hay partidos de eliminatoria jugados.')
    rules = (
        '<div class="ko-rules"><b>Fase eliminatoria — puntuación:</b> '
        'misma regla que grupos (+1 ganador, +1 goles del local, +1 goles del visitante; '
        'máx. 3 por partido). Estos puntos <b>ya están sumados a la tabla general de arriba</b>.'
        + jugados + '</div>'
    )
    bodies = ""
    pendientes = []
    for p in PLAYERS:
        b = players.get(p)
        if b:
            s = scores.get(p, {})
            bodies += render_player_bracket(
                p, b, real_index, s.get("ko_detail"),
                s.get("ko", 0), s.get("ko_played", 0))
        else:
            pendientes.append(p)
    if pendientes:
        bodies += (f'<div class="ko-pending">⏳ Bracket pendiente de: '
                   f'<b>{", ".join(pendientes)}</b>. En cuanto manden su Excel se agrega aquí.</div>')
    return f"""
  <section>
    <h2>🏅 Fase Eliminatoria</h2>
    {KO_CSS}
    {rules}
    {bodies}
  </section>"""


def build_pred_index(quinielas):
    """player -> {(grupo, frozenset(equipos)): pred}"""
    idx = {}
    for player in PLAYERS:
        idx[player] = {}
        data = quinielas.get(player, {})
        for group, matches in data.items():
            if group == "terceros":
                continue
            for m in matches:
                key = (group, frozenset((m["team1"], m["team2"])))
                idx[player][key] = m
    return idx


def main():
    quinielas = load_json("quiniela_data.json")
    fixtures = load_json("fixtures.json")
    pred_idx = build_pred_index(quinielas)

    # ---- Validación de consistencia de nombres ----
    problemas = []
    for fx in fixtures:
        key = (fx["group"], frozenset((fx["home"], fx["away"])))
        for player in PLAYERS:
            if key not in pred_idx[player]:
                problemas.append(f"{player}: sin predicción para {fx['home']} vs {fx['away']} ({fx['group']})")

    # ---- Cálculo de puntos ----
    scores = {p: {"points": 0, "exact": 0, "result": 0, "local": 0, "visit": 0,
                  "wrong": 0, "played": 0, "pending": 0, "pred_goals": 0} for p in PLAYERS}

    # total de goles predichos (todos los partidos)
    for player in PLAYERS:
        for key, m in pred_idx[player].items():
            scores[player]["pred_goals"] += (m.get("goals1") or 0) + (m.get("goals2") or 0)

    real_total_goals = 0
    for fx in fixtures:
        if fx["status"] == "FT":
            real_total_goals += (fx["homeGoals"] or 0) + (fx["awayGoals"] or 0)

    # detalle por partido (para tabla)
    detalle = []  # cada item: dict con fixture + picks por jugador
    for fx in sorted(fixtures, key=lambda x: (x["date"], x["group"])):
        key = (fx["group"], frozenset((fx["home"], fx["away"])))
        played = fx["status"] == "FT"
        row = {"fx": fx, "picks": {}}
        for player in PLAYERS:
            m = pred_idx[player].get(key)
            if not m:
                row["picks"][player] = None
                continue
            # orientar predicción a local/visitante del fixture
            if m["team1"] == fx["home"]:
                p_home, p_away = m["goals1"], m["goals2"]
            else:
                p_home, p_away = m["goals2"], m["goals1"]
            if played:
                pts, exacto, tags = points_for(p_home, p_away, fx["homeGoals"], fx["awayGoals"])
                scores[player]["points"] += pts
                scores[player]["played"] += 1
                if exacto:
                    scores[player]["exact"] += 1
                elif pts == 0:
                    scores[player]["wrong"] += 1
                else:
                    if "Resultado" in tags: scores[player]["result"] += 1
                    if "Local" in tags: scores[player]["local"] += 1
                    if "Visitante" in tags: scores[player]["visit"] += 1
                row["picks"][player] = {"ph": p_home, "pa": p_away, "pts": pts, "exact": exacto}
            else:
                scores[player]["pending"] += 1
                row["picks"][player] = {"ph": p_home, "pa": p_away, "pts": None, "exact": False}
        detalle.append(row)

    # ---- Puntos de fase eliminatoria (misma regla que grupos) ----
    knockout = load_json_optional("knockout_data.json")
    ko_real = (knockout or {}).get("real_matches", []) or []
    ko_players = (knockout or {}).get("players", {})
    for p in PLAYERS:
        b = ko_players.get(p)
        ks = score_ko_player(b, ko_real) if b else {
            "pts": 0, "exact": 0, "played": 0, "per_pair": {}}
        scores[p]["ko"] = ks["pts"]
        scores[p]["ko_exact"] = ks["exact"]
        scores[p]["ko_played"] = ks["played"]
        scores[p]["ko_detail"] = ks["per_pair"]
        scores[p]["total"] = scores[p]["points"] + ks["pts"]

    # ---- Orden con desempates (por TOTAL: grupos + eliminatoria) ----
    ranking = sorted(
        PLAYERS,
        key=lambda p: (scores[p]["total"], scores[p]["exact"] + scores[p]["ko_exact"],
                       -abs(scores[p]["pred_goals"] - real_total_goals)),
        reverse=True,
    )

    knockout_html = render_knockout(knockout, scores)

    html = render(scores, ranking, detalle, real_total_goals, problemas, knockout_html)
    out = os.path.join(WORKSPACE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    # ---- Reporte en consola ----
    print(f"✅ index.html generado — {datetime.now():%Y-%m-%d %H:%M:%S}")
    jugados = sum(1 for fx in fixtures if fx["status"] == "FT")
    print(f"   Partidos con resultado: {jugados}/72 | Goles reales acumulados: {real_total_goals}")
    print("   Tabla:")
    for i, p in enumerate(ranking, 1):
        s = scores[p]
        print(f"   {i}. {p}: {s['total']} pts (grupos {s['points']} + elim {s['ko']}; "
              f"exactos {s['exact']+s['ko_exact']}, jugados {s['played']+s['ko_played']})")
    if problemas:
        print("\n⚠️  PROBLEMAS DE EMPAREJAMIENTO:")
        for x in problemas:
            print("   -", x)
    else:
        print("   ✔ Todos los partidos emparejaron con las 4 predicciones.")


# ===========================================================================
#  RENDER HTML
# ===========================================================================
MEDALS = ["🥇", "🥈", "🥉", "4️⃣"]


def cell_pick(pick):
    if pick is None:
        return '<td class="na">—</td>'
    ph, pa = pick["ph"], pick["pa"]
    if pick["pts"] is None:  # pendiente
        return f'<td class="pend">{ph}-{pa}</td>'
    if pick["exact"]:
        return f'<td class="exact">{ph}-{pa} <span class="pp">+3</span></td>'
    if pick["pts"] == 0:
        return f'<td class="wrong">{ph}-{pa} <span class="pp">0</span></td>'
    return f'<td class="part">{ph}-{pa} <span class="pp">+{pick["pts"]}</span></td>'


def render(scores, ranking, detalle, real_total_goals, problemas, knockout_html=""):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    jugados = sum(1 for r in detalle if r["fx"]["status"] == "FT")

    cards = ""
    for i, p in enumerate(ranking):
        s = scores[p]
        cards += f"""
      <div class="card rank{i+1}">
        <div class="medal">{MEDALS[i]}</div>
        <div class="pname">{p}</div>
        <div class="pts">{s['total']}<span>pts</span></div>
        <div class="brk2">🏆 {s['points']} grupos · 🏅 +{s['ko']} elim</div>
        <div class="brk">
          <span title="Marcadores exactos">🎯 {s['exact']+s['ko_exact']} exactos</span>
          <span title="Aciertos parciales">➕ {s['result']+s['local']+s['visit']} parciales</span>
          <span title="Sin acertar">❌ {s['wrong']}</span>
        </div>
        <div class="brk2">Goles predichos: {s['pred_goals']} · Jugados: {s['played']+s['ko_played']}</div>
      </div>"""

    # tabla cronológica
    filas = ""
    last_date = None
    for r in detalle:
        fx = r["fx"]
        if fx["date"] != last_date:
            filas += f'<tr class="daysep"><td colspan="6">{fecha_corta(fx["date"])} de 2026</td></tr>'
            last_date = fx["date"]
        if fx["status"] == "FT":
            real = f'<span class="score">{fx["homeGoals"]}-{fx["awayGoals"]}</span>'
        else:
            real = '<span class="vs">vs</span>'
        gtag = fx["group"].replace("Grupo ", "")
        filas += (
            f'<tr><td class="match"><span class="grp">{gtag}</span> '
            f'{fx["home"]} <b>—</b> {fx["away"]}</td>'
            f'<td class="real">{real}</td>'
            + cell_pick(r["picks"]["Adam"]) + cell_pick(r["picks"]["Diego"])
            + cell_pick(r["picks"]["Fer"]) + cell_pick(r["picks"]["Santiago"])
            + "</tr>"
        )

    aviso = ""
    if problemas:
        aviso = ('<div class="warn">⚠️ Hay predicciones sin emparejar: '
                 + "; ".join(problemas[:6]) + "</div>")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quiniela Mundial 2026</title>
<style>
:root{{--azul:#0d1b2a;--azul2:#1b3a5b;--oro:#c7ae4a;--verde:#1a7d3c;--rojo:#9b2226;--gris:#f2f5f9;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,Arial,sans-serif;background:var(--gris);color:#23303d;line-height:1.45}}
.wrap{{max-width:1080px;margin:0 auto;padding:18px}}
header{{background:linear-gradient(135deg,var(--azul),var(--azul2));color:#fff;border-radius:16px;padding:26px 22px;text-align:center;box-shadow:0 6px 18px rgba(13,27,42,.25)}}
header h1{{font-size:1.7rem;letter-spacing:.5px}}
header .sub{{color:var(--oro);margin-top:6px;font-weight:600}}
header .upd{{font-size:.8rem;opacity:.8;margin-top:8px}}
section{{background:#fff;border-radius:14px;padding:18px;margin-top:18px;box-shadow:0 2px 10px rgba(0,0,0,.06)}}
h2{{color:var(--azul);font-size:1.15rem;border-bottom:3px solid var(--oro);padding-bottom:8px;margin-bottom:14px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}}
.card{{border:1px solid #e6ebf1;border-radius:14px;padding:16px;text-align:center;position:relative;background:#fff}}
.card.rank1{{border-color:var(--oro);box-shadow:0 0 0 2px var(--oro) inset}}
.medal{{font-size:1.6rem}}
.pname{{font-weight:700;font-size:1.2rem;color:var(--azul);margin:2px 0}}
.pts{{font-size:2.3rem;font-weight:800;color:var(--verde)}}
.pts span{{font-size:.85rem;color:#7a8794;margin-left:4px;font-weight:600}}
.brk{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;font-size:.82rem;margin-top:6px;color:#42525f}}
.brk2{{font-size:.74rem;color:#8693a0;margin-top:6px}}
.rules{{background:#fff8e6;border-left:4px solid var(--oro);padding:12px 16px;border-radius:0 10px 10px 0;font-size:.9rem}}
.rules b{{color:var(--azul)}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}
th,td{{padding:8px 6px;text-align:center;border-bottom:1px solid #eef2f6}}
th{{background:var(--azul);color:#fff;font-weight:600;position:sticky;top:0}}
td.match{{text-align:left;font-size:.86rem;white-space:nowrap}}
.grp{{display:inline-block;background:var(--azul);color:#fff;border-radius:5px;font-size:.68rem;padding:1px 6px;margin-right:5px;font-weight:700}}
.real .score{{font-weight:800;color:var(--azul);font-size:1.02rem}}
.real .vs{{color:#aab4be;font-size:.8rem}}
.daysep td{{background:#eef3f8;color:var(--azul2);font-weight:700;text-align:left;font-size:.82rem;text-transform:uppercase;letter-spacing:.5px}}
.exact{{background:#e7f6ec;color:var(--verde);font-weight:700}}
.part{{color:var(--verde)}}
.wrong{{color:var(--rojo)}}
.pend{{color:#9aa6b2;font-style:italic}}
.na{{color:#cbd3db}}
.pp{{font-size:.7rem;opacity:.8}}
.tablewrap{{overflow-x:auto}}
.warn{{background:#fde8e8;border-left:4px solid var(--rojo);padding:10px 14px;border-radius:0 8px 8px 0;font-size:.85rem;margin-bottom:12px}}
footer{{text-align:center;color:#8693a0;font-size:.78rem;padding:22px 10px}}
@media(max-width:620px){{header h1{{font-size:1.3rem}}th,td{{padding:6px 3px;font-size:.78rem}}td.match{{white-space:normal}}}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>⚽ Quiniela Mundial 2026</h1>
    <div class="sub">Seguimiento en vivo · {jugados}/72 partidos jugados</div>
    <div class="upd">Actualizado: {now}</div>
  </header>

  {aviso}

  <section>
    <h2>🏆 Tabla de posiciones</h2>
    <div class="cards">{cards}
    </div>
  </section>

  <section>
    <div class="rules">
      <b>Puntuación:</b> +1 ganador/empate · +1 goles del local · +1 goles del visitante (máx. 3 por partido).<br>
      <b>Desempate:</b> 1) más marcadores exactos · 2) más cercano al total de goles del torneo
      (real acumulado: <b>{real_total_goals}</b>).<br>
      <b>Premios:</b> 🥇 60% · 🥈 20% · 🥉 10% · Organización 10%
    </div>
  </section>

  <section>
    <h2>📊 Resultados y pronósticos</h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>Partido</th><th>Real</th><th>Adam</th><th>Diego</th><th>Fer</th><th>Santiago</th></tr></thead>
      <tbody>{filas}</tbody>
    </table>
    </div>
  </section>
{knockout_html}
  <footer>
    Generado automáticamente desde <code>fixtures.json</code> + <code>quiniela_data.json</code>.<br>
    Los resultados se emparejan por equipos contra el calendario oficial de la FIFA.
  </footer>
</div>
</body>
</html>"""


if __name__ == "__main__":
    main()
