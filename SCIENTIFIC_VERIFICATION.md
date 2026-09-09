# Abell Nexus — Verificación Científica

> **Documento Secundario Derivado** | Interfaz interactiva para investigadores: [🔬 Dashboard de Verificación](https://abell-systems.github.io/nexus/#/scientific-verification)

![Estado](https://img.shields.io/badge/Verificaci%C3%B3n_Cient%C3%ADfica-PASS-brightgreen) ![Commit](https://img.shields.io/badge/Commit-c1620df-blue) ![Dataset](https://img.shields.io/badge/Dataset-nexus--pilot--16-purple)

## 1. Trazabilidad Puntual (Point-in-Time Provenance)

- **Estado de Integridad Científica:** `PASS`
- **Estado Global del Proyecto:** `PASS`
- **Commit Evaluado:** `c1620df0d5e8a5b044ddff0a1a80694796950ce6`
- **Fecha de Evaluación:** `2026-09-09T07:07:31.361549+00:00`
- **Corpus Auditado:** `nexus-pilot-16-evaluation-corpus-v1`

## 2. ¿Qué es Abell Nexus?

Abell Nexus es un motor de emparejamiento tecnológico causal para patentes y demandas industriales. Su objetivo es validar si un modelo semántico causal puede identificar prior art relevante respetando estrictamente la flecha temporal de la innovación.

## 3. Pilares de Verificación Científica

### A. Integridad de los Datos
- **Integridad del Corpus:** Manifiesto y sidecars SHA-256 validados determinísticamente.
- **Correspondencia de Embeddings:** Los vectores corresponden byte a byte a las descripciones analizadas.
- **Ausencia de Duplicados o Registros Huérfanos:** Coherencia relacional verificada.

### B. Protocolo Temporal
- **Regla Temporal Estricta:** La evidencia de prior art debe tener fecha anterior a la fecha de prioridad del target.
- **Excepciones Documentadas:** 3 violaciones temporales congeladas identificadas en el corpus piloto, aceptadas y documentadas formalmente según **ADR-0018 §6 / ADR-0019** (`3 temporal violations formally accepted as exceptions under ADR-0018/ADR-0019 (accepted_temporal_exception)`).

### C. Reproducibilidad
- **Identificadores Inmutables:** Dataset y artefactos versionados mediante hashes criptográficos.
- **Auditoría Automatizada:** Verificación ejecutable en integración continua (CI) mediante `scripts/audit_project_status.py`.

## 4. Frontera Epistemológica

### Demostrado con Evidencia Objetiva
1. Integridad byte-a-byte del corpus piloto frente a sus manifiestos criptográficos SHA-256.
2. Trazabilidad reproducible confirmada de embeddings y matrices de características.
3. Cumplimiento del protocolo temporal bajo las excepciones formalmente gobernadas (ADR 0018/0019).

### No Demostrado Aún (Límites Actuales)
1. **Generalización Estadística:** No se ha demostrado sobre catálogos industriales a gran escala (>100.000 patentes).
2. **Validez Transfronteriza:** No se ha evaluado fuera de las jurisdicciones del piloto.
3. **Eficacia Universal:** No se afirma validez universal del modelo.

### Siguiente Paso Científico (Fase 2)
Construir el pool de candidatos ampliado (N=39), ejecutar anotación ciega dual independiente y medir el coeficiente Kappa/IAA (ADR 0019).

---

*Reporte generado determinísticamente a partir de `project_status.json` bajo ADR 0022.*
