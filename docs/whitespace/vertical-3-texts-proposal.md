# Vertical 3: proposed Spanish texts (draft for approval)

**Status:** Proposal. **None of these texts is approved.** Nothing is implemented, and the screen waits for the approval of this document.
**Date:** 2026-10-26
**Checks:** [vertical 3 contract](product-vertical-3-contract.md) §3, §4, §8 (M3, M5) · [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) E4, E6
**Scope:** The texts of the view, by the state of the system they describe, so that an empty result, missing data, a blocked view and an error are not mistaken for each other. Each text says whether it is **new** or an **existing constant**, and whether it belongs to the closed allowlist of the contract. This is the proposal on which scenario M3 will be run; it does not replace M3.

## 1. Rules applied

* The states reflect real conditions of the system. No text turns a missing or blocked state into something that reads as a result, and no "no results" text is used for a failure to load.
* The closed list of forbidden words of the contract (§4) was checked against every text below, as whole terms, without distinguishing case or accents, singular and plural. The check was an ad hoc script run for this proposal; the test that will guard the screen is a separate piece of work. Result: the only texts that contain a listed word are the three allowlisted sentences (T03, T05, T06) and one existing sentence that is **not** allowlisted (T23).
* Placeholders in braces are filled with values read from the data or the gate; they never carry judgement.
* Spanish, as in the other verticals.

## 2. Texts by state

### 1. Results available

| Id | Text | Origin | Listed words found |
|---|---|---|---|
| T01 | Pares no observados (exploratorio) | new; titulo | none |
| T02 | Exploratorio. Sin validar. Ningún orden mostrado aquí es una predicción. El estudio no ha demostrado que ningún orden prediga nada (ADR 0036). | new; aviso | none |
| T03 | Orden por esperado bajo independencia: refleja cuántas coincidencias se esperarían si las dos subclases fueran independientes; no mide probabilidad de aparición ni interés. | allowlist (new, closed list of the contract §4); aviso orden | probabilidad |
| T04 | Parámetros fijados por diseño, no ajustados a los resultados: una subclase es activa con al menos 20 identificadores de publicación; el esperado mínimo para el tipo con esperado ≥ 1 es 1. | new; parametros | none |
| T05 | Una ausencia observada indica que no se ha observado co-clasificación en este corpus y periodo. No demuestra que las áreas no se combinen ni que exista una oportunidad tecnológica. | allowlist (existing constant `absenceIsNotOpportunity`, vertical 1); ausencia (constante existente) | oportunidad |
| T06 | White spaces predictivos: no disponible. Pendiente de validación científica. | allowlist (existing constant `status`, vertical 1); estado del estudio (constante existente) | white space |
| T07 | Límites del corpus: faltan las publicaciones de tipo Y de 2000 a 2009 y todo el año 2010; hay huecos menores en 2011–2020 y una caída de traducciones EP en 2023. Un periodo sin publicaciones en el corpus no se lee como ausencia de actividad. La comparación de completitud es contra el inventario de la OEPM, no contra un recuento independiente. | new; limites | none |
| T09 | Subclase A · Subclase B · Esperado bajo independencia (coincidencias) · Documentos de A · Documentos de B | new; columnas | none |
| T10 | Orden: por símbolo (predeterminado) · por documentos de A · por documentos de B · por esperado bajo independencia (elegido) | new; orden | none |
| T11 | Tipo: todos los pares no observados · Tipo: no observados con esperado ≥ 1 bajo independencia | new; filtros | none |
| T20 | Evidencia del par · Documentos de cada subclase hasta 2025 · Términos del esperado por año · Identidad del corpus y del resultado (SHA-256) | new; evidencia titulos | none |
| T21 | Documentos con ambas: 0 (par no observado en este corpus y periodo). | new; par documentos | none |

### 2. Legitimately empty

| Id | Text | Origin | Listed words found |
|---|---|---|---|
| T12 | Ningún par cumple estos filtros. Que no haya pares con estos filtros no es un hallazgo. | new; vacio legitimo | none |
| T13 | Esta subclase no tiene pares no observados con las demás subclases activas del corpus hasta 2025. | new; subclase sin pares | none |

### 3. Nothing shown yet (initial state, loading) and data not available

| Id | Text | Origin | Listed words found |
|---|---|---|---|
| T08 | Elige una subclase o una sección para empezar. No se muestra ningún par hasta entonces. | new; estado inicial | none |
| T14 | Cargando los datos… | new; cargando | none |
| T15 | Los datos de pares no observados no están disponibles en este momento. No se muestra ningún resultado. | new; no disponible | none |
| T22 | La lista de identificadores de esta subclase no está disponible. No se muestra la evidencia de actividad. | new; lista no disponible | none |

### 4. View blocked or not published

| Id | Text | Origin | Listed words found |
|---|---|---|---|
| T16 | Los datos de esta vista no están publicados todavía. No se muestra ningún resultado. | new; no publicado | none |
| T17 | Vista bloqueada: el corpus de 2025 no cumple el criterio de completitud. No se muestra ningún par. | new; bloqueo completitud | none |

### 5. Load or validation error

| Id | Text | Origin | Listed words found |
|---|---|---|---|
| T18 | No se pudieron cargar los datos. No se muestra ningún resultado. Puede reintentar. | new; error de carga | none |
| T19 | Los datos cargados no superan la comprobación de integridad. No se muestra ningún resultado. | new; error de validacion | none |

### Existing text that must not appear on this view as it stands

| Id | Text | Origin | Listed words found |
|---|---|---|---|
| T23 | Sin puntuación ni ranking: el orden lo elige quien consulta y se etiqueta con el nombre de la columna. | existing constant; explorador noScore (constante existente de la vertical 2) | ranking, puntuacion |

## 3. Points the proposal raises

1. **T23 is an existing sentence of the explorer (vertical 2) and contains «ranking» and «puntuación».** It is not on the allowlist, so it must not appear on this view. Either it is not shown here (the proposal) or the contract is amended to add it to the allowlist. The view uses T02 and the labelled sort instead.
2. **T03, T05 and T06 contain listed words by design.** They are negations or limits (the quantity does not measure probability; an absence is not an opportunity; the predictive white spaces are not available). Whether each one denies and does not affirm is the human check of M3.
3. **«Vista bloqueada» (T17) and «no publicado» (T16) describe what the page can observe, not what enforces the block.** The barrier is the server and the exposure authorisation; the page only reports that the data was refused or the gate did not pass. A text must not suggest that the page itself grants or denies access.
4. **T19 («comprobación de integridad»)** assumes the browser verifies the data against the hash in `provenance.json` before drawing it. The contract does not require that today, only the tests do. Either the screen implements the check, or T19 is removed. Decision for the review.
5. **T22** depends on E5, which is not decided; if the lists are not available the evidence view has a smaller form and T20/T22 change.
6. **«Esperado»** is shortened from «esperado bajo independencia» in some labels; the full phrase is kept wherever the quantity is first named in a view, and the shortened form is a decision for the review.
7. **T07** adds the 2023 drop of EP translations and the sentence about the inventory comparison to the limits text of the explorer; both come from ADR 0036 and the contract, and neither has been shown to a reader yet.

## 4. Approval

The owner and the reviewer approve, change or reject each text. Until then the texts in the contract stay proposals, the screen is not written, and nothing is exposed. Approval of the texts does not authorise exposure: the completeness gate, the access record, M1–M7 and the visual review still apply.
