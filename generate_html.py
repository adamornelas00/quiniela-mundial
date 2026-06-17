import json
import os
from datetime import datetime

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
    if real.get("pending", True):
        return 0, "Pendiente", 0
    
    pg1 = pred["goals1"]
    pg2 = pred["goals2"]
    rg1 = real["goals1"]
    rg2 = real["goals2"]
    
    if pg1 is None or pg2 is None or rg1 is None or rg2 is None:
        return 0, "Sin predicción", 0
    
    pts = 0
    reasons = []
    
    pred_winner = get_winner(pg1, pg2)
    real_winner = get_winner(rg1, rg2)
    if pred_winner == real_winner:
        pts += 1
        reasons.append("Resultado")
    
    if pg1 == rg1:
        pts += 1
        reasons.append("Local")
    
    if pg2 == rg2:
        pts += 1
        reasons.append("Visitante")
    
    is_exact = (pg1 == rg1 and pg2 == rg2)
    desc = "Exacto" if is_exact else (" / ".join(reasons) if reasons else "Incorrecto")
    return pts, desc, is_exact

def generate_html():
    workspace = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(workspace, "quiniela_data.json")
    results_path = os.path.join(workspace, "results.json")
    output_path = os.path.join(workspace, "index.html")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        quinielas = json.load(f)
    
    real_results = {}
    if os.path.exists(results_path):
        with open(results_path, 'r', encoding='utf-8') as f:
            raw_results = json.load(f)
        # Convert to tuple keys
        for group, matches in raw_results.items():
            for match_num, result in matches.items():
                real_results[(group, int(match_num))] = result
    
    now = datetime.now().strftime("%d de %B de %Y, %H:%M")
    
    scores = {name: {"points": 0, "exact": 0, "winner": 0, "local": 0, "visit": 0, "wrong": 0, "pending": 0, "total_matches": 0, "total_goals_pred": 0} for name in quinielas}
    
    for name in quinielas:
        for group in quinielas[name]:
            if group == "terceros":
                continue
            for match in quinielas[name][group]:
                key = (group, match["match"])
                real = real_results.get(key, {"pending": True})
                
                scores[name]["total_goals_pred"] += (match["goals1"] or 0) + (match["goals2"] or 0)
                
                if not real.get("pending", True):
                    pts, desc, is_exact = calculate_points(match, real)
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
    
    for name in quinielas:
        for group in quinielas[name]:
            if group == "terceros":
                continue
            for match in quinielas[name][group]:
                key = (group, match["match"])
                real = real_results.get(key, {"pending": True})
                
                if real.get("pending", True):
                    real_display = '<span class="pending">Pendiente</span>'
                    match_label = f"{match['team1']} vs {match['team2']}"
                else:
                    real_display = f'<span class="score">{real["goals1"]} - {real["goals2"]}</span>'
                    match_label = f"{match['team1']} vs {match['team2']}"
                
                html += f"<tr><td><strong>{match_label}</strong><br><small style='color:#888'>{match['date']}</small></td><td>{real_display}</td>"
                
                for p_name in ["Adam", "Diego", "Fer", "Santiago"]:
                    p_match = None
                    for m in quinielas[p_name].get(group, []):
                        if m["match"] == match["match"]:
                            p_match = m
                            break
                    
                    if not p_match or p_match["goals1"] is None or p_match["goals2"] is None:
                        html += '<td class="pending">-</td>'
                    elif real.get("pending", True):
                        html += f'<td class="pending">{p_match["goals1"]}-{p_match["goals2"]}</td>'
                    else:
                        pts, desc, is_exact = calculate_points(p_match, real)
                        if is_exact:
                            cls = "exact"
                            label = f"{p_match['goals1']}-{p_match['goals2']} (3p)"
                        elif desc == "Incorrecto":
                            cls = "wrong"
                            label = f"{p_match['goals1']}-{p_match['goals2']} (0p)"
                        else:
                            cls = "result"
                            label = f"{p_match['goals1']}-{p_match['goals2']} ({pts}p)"
                        html += f'<td class="{cls}">{label}</td>'
                
                html += "</tr>\n"
            break
        break
    
    # Wait, I need to iterate over all groups and all matches, not break early
    # Let me redo this loop properly
    html_parts = []
    for group in [f"Grupo {c}" for c in "ABCDEFGHIJKL"]:
        for match_num in range(1, 7):
            # Get match data from any participant (they all have same structure)
            match_data = None
            for p_name in quinielas:
                for m in quinielas[p_name].get(group, []):
                    if m["match"] == match_num:
                        match_data = m
                        break
                if match_data:
                    break
            
            if not match_data:
                continue
            
            key = (group, match_num)
            real = real_results.get(key, {"pending": True})
            
            if real.get("pending", True):
                real_display = '<span class="pending">Pendiente</span>'
                match_label = f"{match_data['team1']} vs {match_data['team2']}"
            else:
                real_display = f'<span class="score">{real["goals1"]} - {real["goals2"]}</span>'
                match_label = f"{match_data['team1']} vs {match_data['team2']}"
            
            row = f"<tr><td><strong>{match_label}</strong><br><small style='color:#888'>{match_data['date']}</small></td><td>{real_display}</td>"
            
            for p_name in ["Adam", "Diego", "Fer", "Santiago"]:
                p_match = None
                for m in quinielas[p_name].get(group, []):
                    if m["match"] == match_num:
                        p_match = m
                        break
                
                if not p_match or p_match["goals1"] is None or p_match["goals2"] is None:
                    row += '<td class="pending">-</td>'
                elif real.get("pending", True):
                    row += f'<td class="pending">{p_match["goals1"]}-{p_match["goals2"]}</td>'
                else:
                    pts, desc, is_exact = calculate_points(p_match, real)
                    if is_exact:
                        cls = "exact"
                        label = f"{p_match['goals1']}-{p_match['goals2']} (3p)"
                    elif desc == "Incorrecto":
                        cls = "wrong"
                        label = f"{p_match['goals1']}-{p_match['goals2']} (0p)"
                    else:
                        cls = "result"
                        label = f"{p_match['goals1']}-{p_match['goals2']} ({pts}p)"
                    row += f'<td class="{cls}">{label}</td>'
            
            row += "</tr>"
            html_parts.append(row)
    
    # Rebuild the HTML with the correct table body
    html = html.split("<tbody>")[0] + "<tbody>\n" + "\n".join(html_parts) + """
</tbody>
</table>
</div>

<div class="section">
<h2>📝 Resumen de predicciones por grupo</h2>
"""
    
    for group in [f"Grupo {c}" for c in "ABCDEFGHIJKL"]:
        html += f"<h3 style='margin:16px 0 8px; color:#2e5f8a;'>{group}</h3>"
        html += "<table><thead><tr><th>Partido</th><th>Fecha</th><th>Real</th><th>Adam</th><th>Diego</th><th>Fer</th><th>Santiago</th></tr></thead><tbody>"
        for match_num in range(1, 7):
            match_data = None
            for p_name in quinielas:
                for m in quinielas[p_name].get(group, []):
                    if m["match"] == match_num:
                        match_data = m
                        break
                if match_data:
                    break
            
            if not match_data:
                continue
            
            key = (group, match_num)
            real = real_results.get(key, {"pending": True})
            
            if real.get("pending", True):
                real_text = "Pendiente"
            else:
                real_text = f'{real["goals1"]}-{real["goals2"]}'
            
            html += f"<tr><td>{match_data['team1']} vs {match_data['team2']}</td><td>{match_data['date']}</td><td>{real_text}</td>"
            for p_name in ["Adam", "Diego", "Fer", "Santiago"]:
                p_match = None
                for m in quinielas[p_name].get(group, []):
                    if m["match"] == match_num:
                        p_match = m
                        break
                if p_match:
                    html += f'<td>{p_match["goals1"]}-{p_match["goals2"]}</td>'
                else:
                    html += '<td>-</td>'
            html += "</tr>"
        html += "</tbody></table>"
    
    html += """
</div>

<footer>
Generado automáticamente desde quiniela_data.json + results.json.<br>
<strong>¿Cómo actualizar?</strong> Busca los resultados del Mundial y agrégalos a results.json, luego ejecuta: <code>python3 generate_html.py</code>
</footer>
</div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ index.html generado en {output_path}")
    print(f"📅 Actualizado: {now}")
    print()
    print("📊 Scores:")
    for name, data in sorted_scores:
        print(f"  {name}: {data['points']} pts (Exactos: {data['exact']}, Ganador: {data['winner']}, Local: {data['local']}, Visitante: {data['visit']}, Errados: {data['wrong']}, Pendientes: {data['pending']}, Goles predichos: {data['total_goals_pred']})")

if __name__ == "__main__":
    generate_html()
