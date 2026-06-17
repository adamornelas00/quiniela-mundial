#!/usr/bin/env python3
"""
update_quiniela.py - Script standalone para actualizar la quiniela del Mundial 2026

Uso: python3 update_quiniela.py

Reglas de puntuación:
- 1 punto por acertar ganador o empate
- 1 punto por acertar marcador del local
- 1 punto por acertar marcador del visitante
- Máximo 3 puntos por partido

Desempate: 1) Más scores exactos | 2) Más cercano al total de goles del torneo
"""

import json
import os
from datetime import datetime
import urllib.request
import urllib.error
import re

# ============================
# CONFIGURACIÓN - RESULTADOS REALES
# ============================
# Agrega/actualiza los resultados aquí. Formato:
# ("Grupo X", N): {"team1": "Equipo1", "goals1": 2, "team2": "Equipo2", "goals2": 1}

REAL_RESULTS = {
    # GRUPO A - Fecha 1: 11 junio
    ("Grupo A", 1): {"team1": "México", "goals1": 2, "team2": "Sudáfrica", "goals2": 0},
    ("Grupo A", 6): {"team1": "Corea del Sur", "goals1": 2, "team2": "Rep. Checa", "goals2": 1},
    # GRUPO B - Fecha 1: 12 junio
    ("Grupo B", 1): {"team1": "Canadá", "goals1": 1, "team2": "Bosnia-Herz.", "goals2": 1},
    ("Grupo B", 6): {"team1": "Qatar", "goals1": 1, "team2": "Suiza", "goals2": 1},
    # GRUPO C - Fecha 1: 13 junio
    ("Grupo C", 3): {"team1": "Brasil", "goals1": 1, "team2": "Marruecos", "goals2": 1},
    ("Grupo C", 4): {"team1": "Haití", "goals1": 0, "team2": "Escocia", "goals2": 1},
    # GRUPO D - Fecha 1: 13 junio
    ("Grupo D", 1): {"team1": "Estados Unidos", "goals1": 4, "team2": "Paraguay", "goals2": 1},
    ("Grupo D", 6): {"team1": "Australia", "goals1": 2, "team2": "Turquía", "goals2": 0},
    # GRUPO E - Fecha 1: 14 junio
    ("Grupo E", 2): {"team1": "Alemania", "goals1": 7, "team2": "Curazao", "goals2": 1},
    ("Grupo E", 5): {"team1": "Costa de Marfil", "goals1": 1, "team2": "Ecuador", "goals2": 0},
    # GRUPO F - Fecha 1: 14 junio
    ("Grupo F", 3): {"team1": "Países Bajos", "goals1": 2, "team2": "Japón", "goals2": 2},
    ("Grupo F", 4): {"team1": "Suecia", "goals1": 5, "team2": "Túnez", "goals2": 1},
    # GRUPO G - Fecha 1: 15 junio
    ("Grupo G", 3): {"team1": "Bélgica", "goals1": 1, "team2": "Egipto", "goals2": 1},
    ("Grupo G", 4): {"team1": "Irán", "goals1": 2, "team2": "Nueva Zelanda", "goals2": 2},
    # GRUPO H - Fecha 1: 15 junio
    ("Grupo H", 3): {"team1": "España", "goals1": 0, "team2": "Cabo Verde", "goals2": 0},
    ("Grupo H", 4): {"team1": "Arabia Saudita", "goals1": 1, "team2": "Uruguay", "goals2": 1},
    # GRUPO I - Fecha 1: 16 junio
    ("Grupo I", 2): {"team1": "Francia", "goals1": 1, "team2": "Senegal", "goals2": 0},
    ("Grupo I", 5): {"team1": "Irak", "goals1": 1, "team2": "Noruega", "goals2": 4},
    # GRUPO J - Fecha 1: 16 junio (resultados por confirmar)
    ("Grupo J", 2): {"team1": "Argentina", "goals1": None, "team2": "Argelia", "goals2": None, "pending": True},
    ("Grupo J", 6): {"team1": "Austria", "goals1": None, "team2": "Jordania", "goals2": None, "pending": True},
}

# ============================
# FUNCIONES DE CÁLCULO
# ============================

def get_winner(goals1, goals2):
    if goals1 is None or goals2 is None:
        return None
    if goals1 > goals2:
        return "team1"
    elif goals2 > goals1:
        return "team2"
    else:
        return "draw"

def calculate_points(pred, real):
    if real.get("pending"):
        return 0, "Pendiente", 0
    
    pg1 = pred["goals1"]
    pg2 = pred["goals2"]
    rg1 = real["goals1"]
    rg2 = real["goals2"]
    
    if pg1 is None or pg2 is None or rg1 is None or rg2 is None:
        return 0, "Sin predicción", 0
    
    pts = 0
    reasons = []
    
    # 1 punto por acertar ganador o empate
    pred_winner = get_winner(pg1, pg2)
    real_winner = get_winner(rg1, rg2)
    if pred_winner == real_winner:
        pts += 1
        reasons.append("Resultado")
    
    # 1 punto por acertar marcador del local
    if pg1 == rg1:
        pts += 1
        reasons.append("Local")
    
    # 1 punto por acertar marcador del visitante
    if pg2 == rg2:
        pts += 1
        reasons.append("Visitante")
    
    is_exact = (pg1 == rg1 and pg2 == rg2)
    desc = "Exacto" if is_exact else (" / ".join(reasons) if reasons else "Incorrecto")
    return pts, desc, is_exact

# ============================
# GENERACIÓN DE HTML
# ============================

def generate_html(quinielas, real_results, scores):
    now = datetime.now().strftime("%d de %B de %Y, %H:%M")
    
    sorted_scores = sorted(scores.items(), key=lambda x: (x[1]["points"], x[1]["exact"]), reverse=True)
    
    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quiniela Mundial 2026 - Seguimiento</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, sans-serif; background: #f5f7fa; color: #333; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
header { background: #0d1b2a; color: white; padding: 30px 20px; text-align: center; border-radius: 12px; margin-bottom: 24px; }
header h1 { font-size: 2rem; margin-bottom: 8px; }
header p { color: #c7ae4a; font-size: 1.1rem; }
.scoreboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 30px; }
.card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; border-top: 4px solid #2e5f8a; }
.card .name { font-size: 1.3rem; font-weight: bold; color: #0d1b2a; margin-bottom: 8px; }
.card .points { font-size: 2.5rem; color: #1a6b34; font-weight: bold; }
.card .detail { font-size: 0.85rem; color: #666; margin-top: 8px; }
.section { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.section h2 { color: #0d1b2a; margin-bottom: 16px; font-size: 1.3rem; border-bottom: 2px solid #c7ae4a; padding-bottom: 8px; }
.rules { background: #fff8e1; border-left: 4px solid #c7ae4a; padding: 12px 16px; margin-bottom: 20px; border-radius: 0 8px 8px 0; }
.rules strong { color: #0d1b2a; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { padding: 10px 8px; text-align: center; border-bottom: 1px solid #eee; }
th { background: #f0f4f8; color: #0d1b2a; font-weight: 600; }
td:first-child { text-align: left; }
.pending { color: #999; font-style: italic; }
.exact { color: #1a6b34; font-weight: bold; }
.result { color: #2e7d32; }
.wrong { color: #922b21; }
.team { font-weight: 600; }
.score { font-size: 1.1rem; font-weight: bold; color: #0d1b2a; }
footer { text-align: center; padding: 20px; color: #888; font-size: 0.85rem; }
@media (max-width: 600px) {
  .scoreboard { grid-template-columns: 1fr 1fr; }
  table { font-size: 0.8rem; }
  th, td { padding: 6px 4px; }
}
</style>
</head>
<body>
<div class="container">
<header>
<h1>⚽ Quiniela Mundial 2026</h1>
<p>Seguimiento diario | Actualizado: """ + now + """</p>
</header>

<div class="rules">
<strong>Reglas de puntuación:</strong><br>
• 1 punto = Acertar ganador o empate<br>
• 1 punto = Acertar marcador del local<br>
• 1 punto = Acertar marcador del visitante<br>
• Máximo: 3 puntos por partido<br><br>
<strong>Desempate:</strong> 1) Más scores exactos | 2) Más cercano al total de goles del torneo<br>
<strong>Premios:</strong> 🥇 60% | 🥈 20% | 🥉 10% | Organizadores 10%
</div>

<div class="scoreboard">
"""
    
    for name, data in sorted_scores:
        html += f"""
<div class="card">
<div class="name">{name}</div>
<div class="points">{data['points']} pts</div>
<div class="detail">Exactos: {data['exact']} | Ganador/Empate: {data['winner']} | Local: {data['local']} | Visitante: {data['visit']}<br>Errados: {data['wrong']} | Pendientes: {data['pending']}<br>Total goles predichos: {data['total_goals_pred']}</div>
</div>
"""
    
    html += """
</div>

<div class="section">
<h2>📊 Detalle por partido</h2>
<table>
<thead>
<tr>
<th>Partido</th>
<th>Resultado Real</th>
<th>Adam</th>
<th>Diego</th>
<th>Fer</th>
<th>Santiago</th>
</tr>
</thead>
<tbody>
"""
    
    for group in [f"Grupo {c}" for c in "ABCDEFGHIJKL"]:
        for match_num in range(1, 7):
            key = (group, match_num)
            real = real_results.get(key, {"pending": True})
            
            preds = {}
            for name in quinielas:
                group_data = quinielas[name].get(group, [])
                for m in group_data:
                    if m["match"] == match_num:
                        preds[name] = m
                        break
            
            if not preds:
                continue
            
            if real.get("pending"):
                real_display = '<span class="pending">Pendiente</span>'
                t1 = preds[list(preds.keys())[0]]["team1"]
                t2 = preds[list(preds.keys())[0]]["team2"]
                match_label = f"{t1} vs {t2}"
            else:
                real_display = f'<span class="score">{real["goals1"]} - {real["goals2"]}</span>'
                t1 = real["team1"]
                t2 = real["team2"]
                match_label = f"{t1} vs {t2}"
            
            html += f"<tr><td><strong>{match_label}</strong></td><td>{real_display}</td>"
            
            for name in ["Adam", "Diego", "Fer", "Santiago"]:
                pred = preds.get(name)
                if not pred or pred["goals1"] is None or pred["goals2"] is None:
                    html += '<td class="pending">-</td>'
                elif real.get("pending"):
                    html += f'<td class="pending">{pred["goals1"]}-{pred["goals2"]}</td>'
                else:
                    pts, desc, is_exact = calculate_points(pred, real)
                    if is_exact:
                        cls = "exact"
                        label = f"{pred['goals1']}-{pred['goals2']} (3p)"
                    elif desc == "Incorrecto":
                        cls = "wrong"
                        label = f"{pred['goals1']}-{pred['goals2']} (0p)"
                    else:
                        cls = "result"
                        label = f"{pred['goals1']}-{pred['goals2']} ({pts}p)"
                    html += f'<td class="{cls}">{label}</td>'
            
            html += "</tr>\n"
    
    html += """
</tbody>
</table>
</div>

<div class="section">
<h2>📝 Resumen de predicciones por grupo</h2>
"""
    
    for group in [f"Grupo {c}" for c in "ABCDEFGHIJKL"]:
        html += f"<h3 style='margin:16px 0 8px; color:#2e5f8a;'>{group}</h3>"
        html += "<table><thead><tr><th>Partido</th><th>Real</th><th>Adam</th><th>Diego</th><th>Fer</th><th>Santiago</th></tr></thead><tbody>"
        for match_num in range(1, 7):
            key = (group, match_num)
            real = real_results.get(key, {"pending": True})
            preds = {}
            for name in quinielas:
                group_data = quinielas[name].get(group, [])
                for m in group_data:
                    if m["match"] == match_num:
                        preds[name] = m
                        break
            if not preds:
                continue
            
            if real.get("pending"):
                real_text = "Pendiente"
                t1 = preds[list(preds.keys())[0]]["team1"]
                t2 = preds[list(preds.keys())[0]]["team2"]
            else:
                real_text = f'{real["goals1"]}-{real["goals2"]}'
                t1 = real["team1"]
                t2 = real["team2"]
            
            html += f"<tr><td>{t1} vs {t2}</td><td>{real_text}</td>"
            for name in ["Adam", "Diego", "Fer", "Santiago"]:
                pred = preds.get(name)
                if pred:
                    html += f'<td>{pred["goals1"]}-{pred["goals2"]}</td>'
                else:
                    html += '<td>-</td>'
            html += "</tr>"
        html += "</tbody></table>"
    
    html += """
</div>

<footer>
Generado automáticamente desde quiniela_data.json.<br>
Para actualizar resultados, modifica REAL_RESULTS en update_quiniela.py y ejecuta el script.<br>
<strong>¿Cómo usar?</strong> Abre una terminal en esta carpeta y ejecuta: <code>python3 update_quiniela.py</code>
</footer>
</div>
</body>
</html>
"""
    return html

# ============================
# MAIN
# ============================

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(workspace, "quiniela_data.json")
    output_path = os.path.join(workspace, "index.html")
    
    # Leer predicciones
    with open(data_path, 'r', encoding='utf-8') as f:
        quinielas = json.load(f)
    
    # Calcular puntos
    scores = {name: {"points": 0, "exact": 0, "winner": 0, "local": 0, "visit": 0, "wrong": 0, "pending": 0, "total_matches": 0, "total_goals_pred": 0} for name in quinielas}
    
    for group in [f"Grupo {c}" for c in "ABCDEFGHIJKL"]:
        for match_num in range(1, 7):
            key = (group, match_num)
            real = REAL_RESULTS.get(key, {"pending": True})
            
            for name in quinielas:
                group_data = quinielas[name].get(group, [])
                pred = None
                for m in group_data:
                    if m["match"] == match_num:
                        pred = m
                        break
                
                if pred:
                    scores[name]["total_goals_pred"] += (pred["goals1"] or 0) + (pred["goals2"] or 0)
                    if not real.get("pending"):
                        pts, desc, is_exact = calculate_points(pred, real)
                        scores[name]["points"] += pts
                        scores[name]["total_matches"] += 1
                        if is_exact:
                            scores[name]["exact"] += 1
                        elif desc == "Incorrecto":
                            scores[name]["wrong"] += 1
                        else:
                            if "Resultado" in desc:
                                scores[name]["winner"] += 1
                            if "Local" in desc:
                                scores[name]["local"] += 1
                            if "Visitante" in desc:
                                scores[name]["visit"] += 1
                    else:
                        scores[name]["pending"] += 1
    
    # Generar HTML
    html = generate_html(quinielas, REAL_RESULTS, scores)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ index.html actualizado en {output_path}")
    print(f"📅 Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("📊 Scores:")
    for name, data in sorted(scores.items(), key=lambda x: (x[1]["points"], x[1]["exact"]), reverse=True):
        print(f"  {name}: {data['points']} pts (Exactos: {data['exact']}, Ganador: {data['winner']}, Local: {data['local']}, Visitante: {data['visit']}, Errados: {data['wrong']}, Pendientes: {data['pending']}, Goles predichos: {data['total_goals_pred']})")

if __name__ == "__main__":
    main()
