# Quiniela Mundial 2026 — Cómo funciona y cómo activarla

## Qué se arregló

1. **Fechas corregidas.** Ahora todas las fechas salen del calendario oficial de la FIFA
   (vía la API de ESPN), guardado en `fixtures.json`.
2. **Resultados emparejados por equipos, no por número de partido.** Antes un resultado
   se podía asignar al partido equivocado. Se corrigieron 3 errores reales:
   - Grupo D: el 2-0 estaba en Australia–Paraguay; el partido jugado fue **Australia 2-0 Turquía**.
   - Grupo F: Suecia–Túnez decía 1-1; el real fue **5-1**.
   - Grupo J: Austria–Jordania decía 2-1; el real fue **3-1**.
3. **Un solo generador** (`build_site.py`) reemplaza a los dos scripts viejos.
   Los cálculos de puntos y el desempate fueron verificados de forma independiente.

## Tabla actual (20 partidos jugados)

1. 🥇 Adam — 33 pts (5 exactos)
2. 🥈 Diego — 22 pts
3. 🥉 Fer — 21 pts (1 exacto)
4. Santiago — 19 pts

## Cómo se actualiza solo cada hora

Un **GitHub Action** (`.github/workflows/update.yml`) corre en los servidores de GitHub
**cada hora, de 10:00 a 00:00 (medianoche) hora de CDMX**. En cada corrida:

1. `fetch_results.py` consulta la API de ESPN y guarda en `fixtures.json` los marcadores
   de los partidos ya terminados (sólo agrega/actualiza; nunca borra un resultado).
2. `build_site.py` reconstruye `index.html`.
3. Si hubo cambios, hace commit y push solo. GitHub Pages publica en ~1 minuto.

> No depende de tu computadora: funciona aunque la tengas apagada.

## Activación (sólo una vez)

1. **Sube los archivos nuevos:** haz doble clic en `publicar.command`
   (sube el workflow, `fixtures.json`, `build_site.py`, `fetch_results.py` y borra los archivos viejos).
2. **Da permiso de escritura al Action:** en GitHub abre tu repo →
   **Settings → Actions → General → Workflow permissions** → elige
   **"Read and write permissions"** → **Save**.
3. **Pruébalo:** en GitHub, pestaña **Actions** → "Actualizar quiniela" → **Run workflow**.
   Debe correr en verde y, si hay partidos nuevos, actualizar el sitio.

## Si alguna vez quieres corregir un resultado a mano

Edita `fixtures.json` (busca el partido por los equipos), pon `homeGoals`, `awayGoals`
y `"status": "FT"`, y haz doble clic en `publicar.command`. Listo.

## Archivos

| Archivo | Para qué |
|---|---|
| `fixtures.json` | Calendario oficial + resultados reales (la "fuente de la verdad"). |
| `quiniela_data.json` | Predicciones de cada participante (no se toca). |
| `build_site.py` | Genera `index.html`. |
| `fetch_results.py` | Baja resultados reales de ESPN. |
| `.github/workflows/update.yml` | Programa la actualización horaria. |
| `index.html` | El sitio publicado. |
| `publicar.command` | Doble clic para reconstruir y publicar a mano. |
