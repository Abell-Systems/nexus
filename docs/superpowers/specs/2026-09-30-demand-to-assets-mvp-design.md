# Demand → Spanish assets MVP (Product B, phase 1): design

Date: 2026-09-30. Authors: Valentín Liñeiro (CTO), Lydia Bares (CEO), Claude.
Status: draft for review. Depends on: `2026-09-30-operational-dense-retrieval-design.md` (the retrieval engine and its pre-registered probe).

## 1. Purpose

Show, end to end and on real data, this flow:

> A real technology demand enters Abell → the system retrieves potentially relevant Spanish industrial-property assets → it shows why they appear, who holds them, and where the source is.

The audience is an investor or jury who sees one demand, three to five results and traceability to the source in about five minutes. "Sellable" is out of scope for this document: see section 9 (claims).

## 2. Scope

In scope:
- Choose one of the 39 pre-embedded example demands.
- Retrieve the top-K eligible assets with the frozen dense retriever.
- Show per asset: rank, title, type (patent / utility model), holders, inventors, publication date, abstract, the asset's own CPC codes, and links to Google Patents and Espacenet.
- Fixed notices about what the ranking is and is not (section 7).

Out of scope (each needs its own spec): free-text demands (needs live embedding, forbidden by ADR 0014 and a different evidence regime); territorial "unexploited" panel (needs a definition of "unexploited" and a territorial universe); OTRI/transfer contacts (no data); alerts; EP records with a Spanish applicant (excluded by the current eligibility policy, about 10,793 records); LLM-generated explanations (not validatable).

## 3. Input boundary

The MVP serves exactly the 39 demands of `dataset_phase2_demand_corpus_n39.json`, embedded offline by `scripts/generate_operational_embeddings.py`. A demand not in that set is unknown (HTTP 404). The UI calls them "example demands ingested from Innoget"; it never suggests that arbitrary text can be searched.

The backend must not read from `experiments/` (ADR 0026). A product snapshot `data/snapshots/operational_corpus_v1/demands_v1.json` is produced once from the n39 corpus by a script, carrying: `demand_id, title, description, posted_date, origin_country, source_url` (from `provenance.source_uri`) and the sha256 of the source file. All 39 demands are served, including the 8 that the probe reserves as Lab Test demands: the probe protects its evaluation inside `experiments/`; the product shows retrieval only and makes no quality claim.

## 4. Contracts

### 4.1 `GET /api/demand-examples`
Returns `{"demands": [{demand_id, title, description, origin_country, posted_date, source_url}]}` in corpus order. (The existing `GET /api/demands` is bound to the legacy domain slugs and is left untouched.)

### 4.2 `GET /api/matches?demand_id=<id>&limit=<1..10, default 5>`
Success (200):

```json
{
  "demand": {"demand_id": "...", "title": "...", "description": "...", "source_url": "..."},
  "assets": [{
    "rank": 1,
    "publication_id": "ES-2594181-A1",
    "title": "...", "ip_type": "patent|utility_model",
    "country_code": "ES", "kind_code": "A1",
    "assignees": ["..."], "inventors": ["..."],
    "publication_date": "2016-12-16",
    "abstract": "...", "abstract_language": "es|en",
    "cpc_codes": ["..."],
    "source_links": {"google_patents": "https://patents.google.com/patent/ES2594181A1", "espacenet": "..."}
  }],
  "meta": {
    "retrieval": "dense",
    "eligible_count": 0,
    "corpus_id": "NEXUS-OPERATIONAL-CORPUS-V1",
    "corpus_parquet_sha256": "...",
    "embedding_index_sha256": "...",
    "notices": ["..."]
  }
}
```

- `rank` is the only ordering signal exposed. **The raw score and any derived `alta/media/baja` band are not in the response.** A qualitative band is allowed only after the probe result exists and only with a rule fixed in a new spec before anyone looks at scores.
- Unknown `demand_id` → 404 (same pattern as the existing demand route). `limit` outside 1..10 → 422.
- If fewer than `limit` assets are eligible, return fewer; if none, `assets: []` with `eligible_count: 0`. Never pad.
- A missing or hash-mismatched index or corpus aborts the service at startup (fail fast); the route never falls back to BM25 or to a live model.

### 4.3 Asset links
`google_patents`: `https://patents.google.com/patent/` + publication number with dashes removed (`ES-2594181-A1` → `ES2594181A1`). `espacenet`: `https://worldwide.espacenet.com/patent/search?q=pn%3D` + the same compact number. Both are pure string functions; the UI labels them "Fuente".

## 5. Single source of truth for eligibility

The ES-jurisdiction and publication-date-before-demand rule lives in one function, `operational_eligibility_policy()`, returning `DefaultPatentEligibilityPolicy(target_jurisdiction="ES")`. The API wiring and `build_probe_sheets.py` both call it; neither constructs the policy on its own. A test asserts both modules obtain their policy from that function, so the demo and the probe cannot drift into different universes.

## 6. Architecture

- **domain**: no new entity beyond what exists (`PatentDocument` already has assignees, inventors, CPC, dates, family). `load_operational_patents` is extended to fill them from the parquet columns that already exist.
- **application** (`application/matching/`): use case `find_assets_for_demand(demand_id, limit)`; it takes a `PatentCandidateRetriever`, a demand repository protocol and an asset lookup protocol, and returns ranked assets. No HTTP, no numpy.
- **infrastructure**: a read-only `OperationalCorpus` adapter (patents + `ip_type` + `abstract_language` + both hashes), a demand repository over `demands_v1.json`, the existing `NumpyDenseRetriever` and `PrecomputedEmbedder`, and a new `APIRouter` module for the two routes. The router is included before the catch-all `/{full_path:path}` route in `api.py`, or the SPA fallback shadows it.
- **frontend**: one new screen in three steps (choose demand, see results, open asset detail) and a typed client call. Spanish UI strings. The existing `UserZero` component and legacy routes are not modified.

Import Linter and `check_architecture.py` must pass unchanged; the runtime imports no torch/transformers/sentence_transformers.

## 7. What the screen says

Always visible, fixed text:
1. "Ordenado por similitud de recuperación. No garantiza que el activo resuelva la demanda."
2. "Datos: Google Patents Public Data. Licencia en verificación; uso interno."
3. "Cobertura: patentes y modelos de utilidad ES de solicitantes españoles. Las solicitudes EP con solicitante español aún no se incluyen."
4. "Calidad del ranking en evaluación (probe preregistrado)." This sentence is a single constant. It changes only when the result document `docs/operational-dense-probe-result.md` exists, and it then states the outcome as written there, not a paraphrase.

Per asset the panel is titled "Datos del activo": abstract, the asset's own CPC codes (as context, not as a match) and the source links. **There is no "Señales de coincidencia" block in this version.** The 39 demands carry no CPC prefixes (`target_cpc_prefixes` is empty in 39/39), so no demand–asset CPC overlap can exist; showing an empty or implied explanation would mislead. When demands gain CPC, a match-signals block can be specified then.

## 8. Testing

- Use case: ranked order preserved, `limit` honoured, empty result when nothing is eligible, unknown demand raises a domain error.
- API (TestClient over a small synthetic corpus and index): 200 shape with no `score` or band keys anywhere in the JSON; 404 unknown demand; 422 bad limit; fewer-than-limit case; startup failure on a tampered index.
- Links: exact strings for an ES and an EP publication number.
- Eligibility: one policy factory, used by both API and probe builder.
- Loader: assignees, inventors, CPC and dates populated from parquet.
- Frontend: component test for the three states (loading, results, empty) and the four fixed notices present.
- One end-to-end smoke test against the real snapshot and real embeddings, run manually after generation finishes, not in CI.

## 9. Claims this MVP may and may not make

May: "works on real ingested demands over a corpus of 54,997 Spanish industrial-property assets; every result links to its public source; ranking comes from a frozen, versioned multilingual embedding model".
May not, until their gates close: any statement about ranking quality (the probe decides); commercial use or redistribution of the data (licence unverified); "unexploited" assets; any price, demand or market-size figure; "sellable product" in the sense of a customer-ready service. The accurate framing for financing conversations is "validated-prototype MVP on real data, quality evaluation in progress".

## 10. Risks

- The probe may resolve NO or UNRESOLVED. The screen must then keep working but notice 4 states the result; the MVP is not withdrawn, the ranking claim is.
- 39 example demands only: a live demo cannot take a question from the audience. Mitigation: state it on screen and pre-select a demand whose results were read beforehand.
- Licence: an investor who asks "can you sell this data?" gets "not yet verified".
- Evaluator A built the system (declared in the probe spec); the MVP inherits that caveat.
