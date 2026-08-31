# Metodología — Agente de Innovación de Patentes

*Especificación formal del método, pensada como base metodológica para publicación científica. Refleja el código en `backend/patent_agent/` tal cual está implementado (agosto de 2026). Versión en inglés: [methodology.md](methodology.md).*

---

## 1. Resumen

Se propone un sistema multi-agente para la identificación y validación automatizada de oportunidades de invención (*white space*) en paisajes tecnológicos de patentes. El sistema combina (i) minería determinista de datos de patentes, (ii) segmentación taxonómica del paisaje con una métrica compuesta de oportunidad, y (iii) un ciclo generativo-adversarial basado en modelos de lenguaje grande (LLM) cuya salida está sujeta a un requisito arquitectónico de trazabilidad: toda afirmación debe ir acompañada de citas verificables a documentos de patente concretos.

Dominio de evaluación: **electrolitos de estado sólido para baterías de vehículos eléctricos** (dominio fijo durante todo el estudio).

## 2. Fuentes de datos

| Fuente | Contenido | Rol |
|---|---|---|
| Google Patents Public Datasets (BigQuery) | Publicaciones de patentes: número de publicación, título, resumen, titular, inventores, fechas, códigos CPC, recuento de citas | Señal de oferta: qué ya existe |
| SBIR/STTR (EE. UU.) y CORDIS (UE) | Solicitudes abiertas de necesidades tecnológicas | Señal de demanda: qué se necesita |

El sistema define dos contratos de datos (`PatentRecord`, `DemandSignal` en `tools/schemas.py`) y una capa de abstracción que permite sustituir la fuente real por datos simulados controlados (`USE_MOCK_BIGQUERY=true`), lo que garantiza la reproducibilidad de los experimentos sin dependencia de credenciales externas.

## 3. Segmentación del paisaje tecnológico

Las patentes recuperadas para el dominio se agrupan por **prefijo CPC primario** (los primeros 4 caracteres del primer código CPC de cada documento). Cada grupo constituye un clúster tecnológico. Esta segmentación taxonómica es deliberadamente transparente y auditable; la sustitución futura por agrupamiento basado en *embeddings* semánticos está prevista sin cambio alguno en los contratos de salida.

De cada clúster se publican sus tres patentes representativas, seleccionadas por mayor recuento de citas.

## 4. Métrica compuesta de espacio en blanco

Para cada clúster $i$ con $n_i$ patentes, sea $n_{max} = \max_j n_j$. Se definen cuatro señales normalizadas en $[0, 1]$:

**Densidad relativa** (saturación):
$$d_i = \frac{n_i}{n_{max}}$$

**Recencia** — antigüedad media de presentación respecto a un horizonte de 20 años:
$$r_i = \mathrm{clip}\left(1 - \frac{\bar{a}_i}{20},\ 0,\ 1\right), \quad \bar{a}_i = \frac{1}{n_i}\sum_k \max(1,\ y_{hoy} - y_{presentación,k})$$

**Velocidad de citación** — citas por año desde la presentación (interés activo de investigación):
$$v_i = \mathrm{clip}\left(\frac{1}{n_i}\sum_k \frac{c_k}{a_k},\ 0,\ 1\right) \text{ con escala } /10$$

**Demanda** — necesidades tecnológicas abiertas cuyo prefijo CPC coincide con el clúster:
$$q_i = \begin{cases} m_i / m_{max} & \text{si existe alguna señal} \\ 0 & \text{en otro caso}\end{cases}$$

La puntuación de espacio en blanco es la combinación lineal ponderada:

$$W_i = 0.4\,(1 - d_i) + 0.2\, r_i + 0.15\, v_i + 0.25\, q_i$$

Un clúster se declara espacio en blanco si $W_i \geq 0.5$ (umbral por defecto). Los clústeres se ordenan por $W_i$ descendente.

*Justificación de los pesos:* la baja densidad domina (0.40) porque la saturación es el obstáculo primario a la patentabilidad; la demanda (0.25) evita clasificar como oportunidad un área poco densa simplemente porque nadie la quiere; recencia (0.20) y velocidad de citación (0.15) descartan áreas abandonadas. La ponderación es un parámetro declarado del método y sensible a análisis.

## 5. Protocolo generativo (agente inventor)

Sobre cada clúster de espacio en blanco, un agente LLM (Gemini, mediante Google ADK) genera candidatos de invención. Cada candidato queda restringido por esquema estructurado (`InventionCandidate`) a cinco campos: identificador, clúster de origen, título, descripción y **novedad reivindicada** (*claimed_novelty*) — la hipótesis específica que será sometida a refutación.

## 6. Protocolo adversarial (agente adversario)

Un segundo agente LLM evalúa cada candidato contra el arte previo disponible. Su salida está restringida por esquema (`AdversarialVerdict`) a:

- `verdict` ∈ {`survives`, `rejected`}
- `rationale` (texto)
- `cited_patents`: **lista obligatoria no vacía** de números de publicación

La restricción `min_length=1` sobre `cited_patents` es estructural (validada en tiempo de ejecución por el esquema): el sistema **rechaza por construcción** cualquier veredicto sin arte previo citado. Este es el mecanismo central de trazabilidad del método: convierte la cita documental de un juicio de IA de recomendación a requisito de validez.

Los agentes inventor y adversario operan en bucle (proponer → criticar → proponer de nuevo) hasta que un candidato sobrevive al escrutinio o se alcanza el número máximo de iteraciones configurado ($k_{max}$, por defecto limitado por cuota).

## 7. Escoración final (agente gobernador)

Los candidatos supervivientes reciben una tarjeta de puntuación (`ScoreCard`) con cuatro dimensiones en $[0,1]$: novedad (`novelty`), riesgo de arte previo (`prior_art_risk`), diferenciación (`differentiation`) y evidencia (`evidence`). Como en §6, el campo `supporting_evidence` tiene cardinalidad mínima 1: toda puntuación debe citar números de publicación trazables a las etapas anteriores del pipeline.

## 8. Cadena completa de custodia de la evidencia

El método garantiza trazabilidad de extremo a extremo:

```
PatentRecord.publication_number  (minería)
   → PatentCluster.representative_patents  (segmentación)
   → AdversarialVerdict.cited_patents  (refutación)
   → ScoreCard.supporting_evidence  (puntuación)
```

Cada número de cita en cualquier etapa puede rastrearse hasta el documento original de patente. No hay ningún eslabón de la cadena que acepte texto libre no verificado como justificación.

## 9. Limitaciones y amenazas a la validez

1. **Segmentación taxonómica**: el agrupamiento por prefijo CPC hereda los sesgos de la clasificación CPC (un invento puede cruzar clases); la granularidad del clúster depende de la consulta de recuperación.
2. **Pesos de la métrica**: los coeficientes de §4 son una elección paramétrica defendible pero no estimada empíricamente; se prestan a calibración con datos de resultados de concesión.
3. **No determinismo del LLM**: las etapas generativas (§5-7) son estocásticas; la reproducibilidad exige fijar temperatura/semilla y reportar variabilidad entre ejecuciones.
4. **Alucinación residual**: el esquema garantiza que las citas *existan* como campos, pero la verificación de que la cita *respalda realmente* el veredicto requiere comprobación humana o automática adicional (línea de trabajo abierta).
5. **Datos simulados**: parte de la validación se realiza contra fuentes simuladas controladas; los resultados con datos reales de BigQuery requieren credenciales GCP.
6. **Cuota de inferencia**: el nivel gratuito de la API (20 peticiones/día por modelo) restringe el número de iteraciones del bucle adversarial por ejecución.

## 10. Reproducibilidad

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # USE_MOCK_BIGQUERY=true por defecto
pytest                            # suite de pruebas unitarias
uvicorn main:app --port 8080     # pipeline determinista vía GET /api/landscape
```

Parámetros declarados del método: umbral de espacio en blanco (0.5), horizonte de recencia (20 años), escala de velocidad de citación (10 citas/año), pesos de §4, iteraciones máximas del bucle (`INVENTION_LOOP_MAX_ITERATIONS`), modelo Gemini (`GEMINI_MODEL`).
