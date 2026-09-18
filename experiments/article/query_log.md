# CEIMAR — Log de consultas Minesoft Origin (MCP)

Fecha de extracción: 2026-09-14
Fuente: servidor MCP `minesoft` (Origin Patent API, https://origin-api.minesoft.com/mcp/)
Input: 247 números de publicación española en `ceimar_raw.txt` (columna "Número de publicación").

## Fase 1 — Normalización (number_lookup)

- Herramienta: `mcp__minesoft__number_lookup`
- Parámetros: `{"number": "<ES nnnnnnn>"}`, una llamada por número.
- 247 líneas originales -> 228 números únicos (19 líneas duplicadas: 16 valores x2, 1 valor x4 [ES2939494]).
- Se llamó una vez por cada uno de los 228 valores únicos.
- Resultado: 228/228 resueltos (familyCount:1 en todos). 2 timeouts transitorios (ES2705529, ES2725569) — reintentados con éxito. 1 número (ES2847162) se omitió por error de transcripción en el primer barrido y se resolvió en una llamada de corrección posterior.
- Regla de selección de ucid cuando `details` trae varias variantes (ej. solicitud A1 + traducción B1/T3/T5): se eligió la primera entrada con `grant: true`; si ninguna lo tenía, la primera disponible.
- Salida consolidada: `lookup_results.json` (228 registros: input, ucid, simplefamily, pd, title).

## Fase 2 — Enriquecimiento (bulk_publications)

- Herramienta: `mcp__minesoft__bulk_publications`
- Parámetros: `{"ids": "<hasta 20 ucids CC-PN-KD separados por coma>", "bibonly": true}`
- Se probó primero con lotes de 100 ucids: la respuesta excedía el límite de la sesión MCP (~10-20 MB por lote de 100, principalmente por el volumen de `legalstatuses` — patentes EP con hasta 60+ eventos INPADOC por país). Se redujo a lotes de 20.
- 12 llamadas (11 x 20 + 1 x 8 ucids) = 228 ucids solicitados, 228 documentos recibidos (0 IDs no encontrados).
- Cada respuesta individual superó el límite de salida inline del entorno y se guardó automáticamente en un fichero de resultado de herramienta; se copiaron sin modificar a `minesoft_raw/batch_01.json` .. `batch_12.json` (formato `{"publications": [...]}`, JSON de Minesoft sin transformar).
- Campos usados de cada documento: `familydata`, `classifications` (ipcr/cpc), `legalstatuses`, `patentstatuses`, `assignees`, `inventors`, `applicants`, `priorities`, `titles`, `backwardcitations`, `forwardcitations`, `docdbfamilyid`.

## Anomalías observadas

1. **Límite de tamaño de lote**: 100 ucids/lote agota el límite de salida del entorno con `bibonly=true` (los `legalstatuses` de patentes EP antiguas son muy verbosos). Lotes de 20 funcionan de forma fiable. Para una repetición futura, usar lotes de 15-20.
2. **Citas backward/forward casi vacías** (3+3 en total sobre 228 docs): los 228 ucids solicitados son las traducciones/validaciones españolas (`-T3`, `-B1`, etc.) de cada familia, y en el registro DOCDB las citas suelen adjuntarse al documento "master" de la familia (la solicitud EP/WO/US original), no a la traducción nacional. Para un citation analysis completo (PASO 15-16) hace falta repetir `bulk_publications`/`get_patent` sobre el miembro líder de cada familia (disponible en `familydata` de cada registro ya descargado), no sobre los ucids ES originales. No se ha hecho en esta pasada — está fuera del alcance pedido ("no interpretar todavía", "solo datos").
3. Un error de transcripción propio omitió `ES2847162` en el primer barrido de `number_lookup`; detectado por verificación cruzada contra el fichero de únicos y corregido antes de pasar a la fase 2.
4. `mcp__minesoft__bulk_publications` devolvió una vez un error `"MCP server session expired"` con un lote de 100 IDs — no era una expiración real de sesión (una llamada `usage` inmediatamente después funcionó); es más probable que fuera un timeout del lado servidor mal etiquetado. Se resolvió reduciendo el tamaño de lote.

## Consumo de cuota

- ~230 llamadas `number_lookup` + 12 `bulk_publications` + varias `usage` de control. Muy por debajo del límite de 100 req/min observado (las llamadas se hicieron secuencialmente, sin ráfagas).

## Fase 3 — Citation analysis sobre el miembro líder de familia (cierre del hueco de los pasos 15-16)

Motivo: las citas backward/forward de la Fase 2 salieron casi vacías (3+3) porque los 228 IDs procesados eran traducciones españolas (-T3/-B1); DOCDB cuelga las citas del documento líder de familia (EP/WO/US), no de la traducción nacional.

### Selección de leader

- Fuente: `familydata.simple-family-data.publications` de cada una de las 227 familias (`docdbfamilyid`), ya presente en los ficheros `minesoft_raw/batch_*.json` de la Fase 2 — no hizo falta ninguna llamada nueva a `number_lookup`.
- Regla fija: preferencia EP > WO > US (miembro más antiguo por `pd` dentro del país preferido); si ninguno de los tres existe, fallback al miembro no-ES más antiguo de la familia (o al miembro ES más antiguo si la familia entera es ES).
- Resultado: **227/227 familias con leader identificado** (0 en `familias_sin_leader_claro`).
- Distribución de `leader_selection_rule`: **EP=221, WO=2, fallback_earliest=4**.
- **Anomalía documentada, no forzada**: el leader `EP-1185536-A2` resultó compartido por dos `docdbfamilyid` distintos (34855248 y 42632476) — probable división/fusión de familia en la base de Minesoft entre dos registros DOCDB relacionados. Se dejó tal cual, sin forzar un desempate arbitrario.
- 226 leaders únicos para 227 familias.

### Enriquecimiento de leaders

- Herramienta: `mcp__minesoft__bulk_publications`, `bibonly=true`, lotes de 20 ids (mismo límite de la Fase 2).
- 12 llamadas, 226/226 leaders recuperados, 0 IDs sin resolver.
- Cada llamada individual excedió el límite de salida del entorno hacia el agente (170k-227k líneas por lote — los `A1`/`A2` de solicitud EP cargan `legalstatuses`/`classifications` muy verbosos) pero el JSON completo se guardó en disco por el propio harness en cada caso; se recuperó y proceso directamente desde esos ficheros sin pérdida de datos. Guardado (sin el campo `familydata`, ya redundante con la Fase 2) en `minesoft_raw/leaders_batch_01.json` .. `leaders_batch_12.json`.

### Resultado

- **Backward citations: 115 en total, media 0.51/familia, mediana 0.**
- **Forward citations: 420 en total, media 1.85/familia, mediana 0.**
- **171/227 familias (75.3%) con el leader sin ninguna cita (ni backward ni forward).**
- Interpretación honesta (sin entrar en Fase 2 de Lydia): la mayoría de los leaders elegidos son publicaciones **A1/A2** (solicitud, no concesión) — es esperable que muchas solicitudes recientes o sin informe de búsqueda público todavía no tengan citas indexadas. Si Lydia quiere maximizar señal de citas, una vía futura (no ejecutada aquí, fuera del alcance de esta pasada) sería usar el documento **B1/granted** de cada familia en vez de la primera publicación A1/A2, cuando exista.
- Exports: `exports/G_citas_leader.xlsx` — hojas `citas_detalle` (535 filas), `resumen_por_familia` (227 filas), `familias_sin_leader_claro` (0 filas).

### Coste

- 12 llamadas `bulk_publications` adicionales (226 IDs) + llamadas de control. Sin errores de rate-limit.
