# Validación de producto del prototipo (Lydia)

Esta hoja sirve para que una investigadora pueda usar el prototipo y decir si le parece útil. **No es una evaluación científica**: no se calcula P@5, no se compara BM25 con búsqueda densa, no se miden tiempos y no hace falta conocer el algoritmo. Tus respuestas no se convertirán en un resultado científico; esta validación es independiente del probe científico aparcado (Amendment A3 del diseño de retrieval).

## Qué hacer

1. Entra en la URL y con las credenciales que te enviamos.
2. Abre `validation_sheet_v1.csv` (Excel o Google Sheets). Tiene una fila por resultado: 21 demandas × los 5 primeros activos que muestra la pantalla (105 filas). Las columnas técnicas (`demand_id` … `asset_title`) ya están rellenas; **no las cambies**.
3. En la pantalla, elige una demanda de la lista (el `demand_id` también aparece en la URL como `?demanda=`). Empieza por las que conozcas mejor; no hace falta completar las 21.
4. Para cada uno de sus 5 resultados, lee el título y el resumen, y abre la fuente original (Google Patents).
5. Rellena las columnas de esa fila (abajo).
6. Anota en `comment` lo que cambiarías antes de enseñar esto a un tercero (una demanda que no se entiende, un resultado absurdo, un resumen que no permite juzgar, un enlace que no abre...).

## Columnas que rellenas

| Columna | Valores |
|---|---|
| `relevance` | `relevante` / `parcial` / `irrelevante` / `no_puedo_juzgar` (usa este último si el título y el resumen no permiten decidir) |
| `evidence_sufficient` | `si` / `no`: ¿el título y el resumen bastan para entender qué es el activo? |
| `traceability_ok` | `si` / `no`: ¿puedes llegar a la fuente original y confirmar que es ese activo? |
| `comment` | texto libre, opcional |

Juzga solo si el resultado te parece **útil o pertinente para la demanda**, con tu criterio. No hay respuestas correctas ni incorrectas, y no tienes que valorar la interfaz técnica ni la velocidad.

## Para quien analice las respuestas

- La hoja se genera con `python scripts/build_validation_sheet.py <artefactos>`; `rank` y `publication_id` permiten reconstruir exactamente lo que se evaluó. Si cambia el corpus o el índice congelado, hay que regenerar la hoja.
- No incluye puntuaciones de similitud ni método de recuperación, a propósito.
- El prototipo no reclama validación humana del ranking; estas respuestas son feedback de producto.
