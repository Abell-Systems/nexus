# Vertical 3: proposed Spanish texts (draft for approval)

**Status:** Texts approved by the owner on 2026-10-26, and **T19 approved by the owner on 2026-10-27** after the contract amendment (#185, merged as `4c88ecf`) required the browser-side SHA-256 verification; **T22 is not approved**; **T23 is excluded** from this view. This is the approval of the applicable texts only: it does not approve the pull request and does not authorise exposure. **Update 2026-10-27:** the list screen is merged in #187 as an intermediate increment, using the approved texts of this list; it is not exposed and does not satisfy E5. T15, T16 and T17 are not implemented (no signal for them), and T13 and T14 have no test. A partial evidence sheet is a local draft in #193 and uses a text, **S4** (proposal of #192), that stands in for **T22**: neither is approved, and #193 cannot be merged until T22 and S4 are decided here.
**Date:** 2026-10-26
**Checks:** [vertical 3 contract](product-vertical-3-contract.md) §3, §4, §8 (M3, M5) · [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) E4, E6
**Scope:** The texts of the view, by the state of the system they describe, so that an empty result, missing data, a blocked view and an error are not mistaken for each other. Each text says whether it is **new** or an **existing constant**, whether it belongs to the closed allowlist of the contract, and the owner's decision. This is the proposal on which scenario M3 will be run; it does not replace M3.

## 1. Rules applied

* The states reflect real conditions of the system. No text turns a missing or blocked state into something that reads as a result, and no "no results" text is used for a failure to load.
* The closed list of forbidden words of the contract (§4) was checked against every text below, as whole terms, without distinguishing case or accents, singular and plural. The check was an ad hoc script run for this proposal; the test that will guard the screen is a separate piece of work. Result: the only texts that contain a listed word are the three allowlisted sentences (T03, T05, T06) and one existing sentence that is **not** allowlisted (T23, excluded). The list of exceptions is not extended to fit any text.
* Placeholders in braces are filled with values read from the data or the gate; they never carry judgement.
* The short form «Esperado» is used only after the first visible definition of «Esperado bajo independencia».
* Spanish, as in the other verticals.

## 2. Texts by state

### 1. Results available

| Id | Text | Origin | Listed words found | Decision (owner, 2026-10-26) |
|---|---|---|---|---|
| T01 | Pares no observados (exploratorio) | new; titulo | none | Approved |
| T02 | Exploratorio. Sin validar. Ningún orden mostrado aquí es una predicción. El estudio no ha demostrado que ningún orden prediga nada (ADR 0036). | new; aviso | none | Approved |
| T03 | Orden por esperado bajo independencia: refleja cuántas coincidencias se esperarían si las dos subclases fueran independientes; no mide probabilidad de aparición ni interés. | allowlist (new, closed list of the contract §4); aviso orden | probabilidad | Approved |
| T04 | Parámetros fijados por diseño, no ajustados a los resultados: una subclase es activa con al menos 20 identificadores de publicación; el esperado mínimo para el tipo con esperado ≥ 1 es 1. | new; parametros | none | Approved: Keep the full wording in the limits block. |
| T05 | Una ausencia observada indica que no se ha observado co-clasificación en este corpus y periodo. No demuestra que las áreas no se combinen ni que exista una oportunidad tecnológica. | allowlist (existing constant `absenceIsNotOpportunity`, vertical 1); ausencia (constante existente) | oportunidad | Approved: Must stay literal. |
| T06 | White spaces predictivos: no disponible. Pendiente de validación científica. | allowlist (existing constant `status`, vertical 1); estado del estudio (constante existente) | white space | Approved: Must stay literal. |
| T07 | Límites del corpus: faltan las publicaciones de tipo Y de 2000 a 2009 y todo el año 2010; hay huecos menores en 2011–2020. Las traducciones de patentes europeas caen en 2023. Un periodo sin publicaciones en el corpus no se lee como ausencia de actividad. La completitud de 2025 se ha comparado con el inventario de la OEPM (como máximo un 1 % de ausencias por grupo); no es una prueba de integridad absoluta del corpus. | new; limites | none | Approved with change (applied): 2010 gap and the 2023 drop separated; the comparison is attributed to the OEPM inventory; the 1 % is not presented as absolute integrity. |
| T09 | Subclase A · Subclase B · Esperado bajo independencia (coincidencias) · Documentos de A · Documentos de B | new; columnas | none | Approved |
| T10 | Orden: por símbolo (predeterminado) · por documentos de A · por documentos de B · por esperado bajo independencia (elegido) | new; orden | none | Approved with change: Use «Esperado bajo independencia» in full wherever it can be read without context; the short form «Esperado» only after the first visible definition. |
| T11 | Tipo: todos los pares no observados · Tipo: no observados con esperado ≥ 1 bajo independencia | new; filtros | none | Approved |
| T20 | Evidencia del par · Documentos de cada subclase hasta 2025 · Términos del esperado por año · Identidad del corpus (SHA-256 de sus ficheros, registrada en el resultado) y del resultado (SHA-256) | new; evidencia titulos | none | Approved with condition (applied): Titles must be backed by the real schema of the result: the unobserved-pairs result does carry the SHA-256 of the corpus files; the exposure result does not. |
| T21 | Documentos observados con ambas subclases: 0 (par no observado en este corpus y periodo). | new; par documentos | none | Approved with precision (applied): Reworded to «Documentos observados con ambas subclases: 0». |

### 2. Legitimately empty

| Id | Text | Origin | Listed words found | Review (recommendation) |
|---|---|---|---|---|
| T12 | No hay pares que cumplan los filtros seleccionados. Esto no demuestra que no exista actividad tecnológica. | new; vacio legitimo | none | Approved with change (applied): Reworded; checked against the closed list: no listed word. |
| T13 | Esta subclase no tiene pares no observados con las demás subclases activas del corpus hasta 2025. | new; subclase sin pares | none | Approved |

### 3. Nothing shown yet (initial state, loading) and data not available

| Id | Text | Origin | Listed words found | Review (recommendation) |
|---|---|---|---|---|
| T08 | Elige una subclase o una sección para empezar. No se muestra ningún par hasta entonces. | new; estado inicial | none | Approved |
| T14 | Cargando los datos… | new; cargando | none | Approved |
| T15 | Los datos de pares no observados no están disponibles en este momento. No se muestra ningún resultado. | new; no disponible | none | Approved |
| T22 | La lista de identificadores de esta subclase no está disponible. No se muestra la evidencia de actividad. | new; lista no disponible | none | Not approved yet: Depends on E5 (§3.2). |

### 4. View blocked or not published

| Id | Text | Origin | Listed words found | Review (recommendation) |
|---|---|---|---|---|
| T16 | Los datos de esta vista no están publicados todavía. No se muestra ningún resultado. | new; no publicado | none | Approved with condition: Only when the publication of the view is not yet authorised or the data are not published; never in place of a load error. |
| T17 | Vista bloqueada: el corpus de 2025 no cumple el criterio de completitud. No se muestra ningún par. | new; bloqueo completitud | none | Approved with condition: Only when the completeness gate has blocked exposure; the view must not look like the security mechanism. |

### 5. Load or validation error

| Id | Text | Origin | Listed words found | Review (recommendation) |
|---|---|---|---|---|
| T18 | No se pudieron cargar los datos. No se muestra ningún resultado. Puede reintentar. | new; error de carga | none | Approved: «Puede reintentar» only if a retry action exists. |
| T19 | Los datos cargados no superan la comprobación de integridad. No se muestra ningún resultado. | new; error de validacion | none | Approved 2026-10-27. Depends on the browser verifying the SHA-256 against the manifest before rendering, now required by contract §6.1 (#185); the text is shown only in the integrity-error state, whose behaviour is verified by the tests of §8 and scenario M8, none of which has run yet. |

### Existing text that must not appear on this view as it stands

| Id | Text | Origin | Listed words found | Review (recommendation) |
|---|---|---|---|---|
| T23 | Sin puntuación ni ranking: el orden lo elige quien consulta y se etiqueta con el nombre de la columna. | existing constant; explorador noScore (constante existente de la vertical 2) | ranking, puntuacion | Rejected for this view: Contains «ranking» and «puntuación»; not on the closed list; the list is not extended to fit it. |

## 3. Points the review raises

1. **T19 and the integrity check.** The hash in `provenance.json` is a control only if the browser compares the loaded bytes against it before rendering; a test of the error text does not implement that. Recommendation of the review: add the verification to the design of the data load, with a negative test that changes one byte and confirms that no result appears. This is a change to the contract (a requirement, a test, a scenario) and is made there, not here; until it is, T19 stays unapproved. If it is not adopted, T19 is removed or replaced by an error that describes only the validation really performed.
2. **T22 and E5.** The state «identifier list not available» stays in the model of states, but its wording and the behaviour of the detail panel are defined after E5 and the deployment of the lists are decided, not before. The distinction between an available pairs result and unavailable documentary evidence is kept.
3. **Terms.** The contract requires the label «Esperado bajo independencia (coincidencias)» and reserves the forbidden words to three exact sentences (T03, T05, T06), kept literally. The list of exceptions is not extended to accommodate T23; any other listed word outside those sentences keeps failing the test.
4. **T23** is an existing sentence of the explorer (vertical 2) and is not shown on this view; the labelled sort and T02 do its job.
5. **«Vista bloqueada» (T17) and «no publicado» (T16) describe what the page observes, not what enforces the block.** The barrier is the server and the exposure authorisation.

## 4. Approval

Decided by the owner on 2026-10-26, on the review's recommendation:

* **Approved:** T01–T06, T08–T11, T13–T15 and T18.
* **Approved with the editorial changes marked:** T07, T12, T16, T17, T20 and T21. T16, T17 and T18 keep the conditions of use noted in the Decision column. For T10, the rule is approved: «Esperado bajo independencia» in full wherever a label can be read without context, and «Esperado» only after the first visible definition.
* **Approved on 2026-10-27:** T19, after the amendment (#185) was merged. Approving the text does not implement or test the verification.
* **Not approved:** T22, until E5 and the availability of the identifier lists are resolved. Their status does not change here.
* **Excluded from this view:** T23. The closed list of exceptions is not extended.

This is not the approval of the pull request and does not authorise exposure: the completeness gate, the access record, M1–M7 and the visual review still apply, and the list screen is merged only as an intermediate increment (#187), not exposed.
