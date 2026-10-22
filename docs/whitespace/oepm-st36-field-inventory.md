# OEPM ST36 field inventory: what the source states, what the adapter keeps

**Purpose:** evidence for gate 2 of [ADR 0037](../adr/0037-operational-corpus-in-database.md) §5.1 (ST36 fidelity). It is an inventory, not a recommendation: it does not decide what `biblio_v1` stores and it changes no adapter, schema or data.
**Analysed:** adapter `backend/src/main/infrastructure/sources/patent/oepm_biblio.py` at repository revision `bf31123950a5f8d3aa483d33b4d02904ed7c1d0d`; the 26 files pinned in `config/whitespace/oepm_biblio_2000_2025.json` (sha256 verified by the adapter; the census scripts read the same files with the same traversal and preprocessing but do not re-verify hashes).
**Raw results:** [`oepm-st36-census-results.json`](oepm-st36-census-results.json) (census of 102 element paths and the multiplicity checks).

## 1. Method and definitions

* `experiments/oepm/st36_census.py`: for every record that parses (DOCTYPE and control characters removed exactly as the adapter does), counts each element path and each attribute.
* `experiments/oepm/st36_multiplicity.py`: targeted checks on application references, IPC containers and sequence, priority kinds, empty titles.
* Columns: **records** = records containing the path; **total** = occurrences; **max** = maximum occurrences in one record. **records with text** = records in which *at least one* occurrence has non-empty text; it is **not** a count of non-empty occurrences and does not show that a field is always filled.
* Attribute values were not tabulated except where stated; "not determinable" means the census or the code does not establish it.
* Reproduce: `python3 -I experiments/oepm/st36_census.py data/raw/oepm_open OUT.json` and `python3 -I experiments/oepm/st36_multiplicity.py data/raw/oepm_open OUT.json` (about 3 minutes each).

## 2. Coverage

711,888 XML files in the 26 archives: 711,547 parse and 341 do not. The counts equal the adapter's: 341 rejected and 711,547 read (the identity of the individual rejected files was not compared). Every parsed record has `bibliographic-data`, `claims` and `description`.

## 3. Inventory

Class: **Read** = the adapter code consumes it and it reaches `PatentPublication` (evidence: the cited function); **Discarded** = present in the source, not carried into the adapter's result; **Not determinable**.

| Source path (under `es-patent-document`) | records | total | max | Class | Evidence / note |
|---|---|---|---|---|---|
| `@country`, `@doc-number`, `@kind`, `@date-publ` | 711,547 | 711,547 | 1 | Read | `_publication` |
| `@file`, `@lang`, `@id` | 711,547 | 711,547 | 1 | Discarded | not referenced in the adapter |
| `bibliographic-data/publication-reference/document-id/*` | 711,547 | 711,547 | 1 | Discarded | duplicates the root attributes; whether it always equals them was not compared |
| `.../application-reference/document-id/{country,doc-number,kind,date}` | 711,547 | 711,643 | 5 | Read (first only) | `_application_reference`, `_optional_date` use `find` / first match; see §4.1 |
| `.../invention-title` | 711,547 | 711,547 | 1 | Read | text empty in 9 records; `@lang`, `@id` Discarded |
| `.../parties/applicants/applicant` with `addressbook/name`, or `last-name` and `first-name` | 711,542 | 803,288 | 24 | Read (name only) | `_party_names`; entries with no name are dropped (§4.4) |
| `applicant/@sequence`, `@designation`, `@app-type`; `address/country`; `nationality/country`; `residence/country` | 711,542 | 803,288 | 24 | Discarded | not referenced |
| `.../parties/inventors/inventor` with `addressbook/name`, or `last-name` and `first-name` | 709,893 | 1,839,897 | 133 | Read (name only) | `name` form in only 174 records; entries with no name are dropped (§4.4) |
| `inventor/@sequence`, `@wishes-to-be-published` (550,589 occurrences); `address/country` | 709,893 | 1,839,897 | 133 | Discarded | not referenced |
| `.../parties/agents/agent/*` | 413,502 | 413,531 | 4 | Discarded | name, address country, `@rep-type`, `@sequence` |
| `.../classifications-ipcr/classification-ipcr/{section,class,subclass,main-group,subgroup}` | 708,798 | 2,617,470 | 222 | Read | `_ipc_entry`; section, class, subclass required, none empty in any occurrence |
| `.../classification-ipcr/ipc-version-indicator/date`, `classification-level`, `classification-value` | 708,798 | 2,617,470 | 222 | Read (raw) | kept in `IpcEntry.version/level/value`; not used by the counts (characterization §5) |
| `.../classification-ipcr/@sequence` | 708,798 | 2,617,470 | 222 | Discarded | but see §4.2: it equals document order |
| `.../priority-claims/priority-claim/date` | 470,631 | 601,780 | 229 | Read | `priority_dates`; unreadable dates become anomalies |
| `priority-claim/{country,doc-number}`, `@kind`, `@sequence` | 470,631 | 601,780 | 229 | Discarded | §4.3 |
| `.../dates-of-public-availability/gazette-reference/{date,gazette-num}` | 711,547 | 711,547 | 1 | Discarded | `date` has text in all records; `gazette-num` has none; whether the gazette date equals the publication date was not compared |
| `.../pct-or-regional-filing-data/document-id/{country,doc-number,date}` | 408,626 | 739,810 | 2 | Discarded | PCT / regional filing |
| `.../pct-or-regional-publishing-data/document-id/{country,doc-number,date,kind}` | 408,494 | 982,392 | 8 | Discarded | PCT / regional publication |
| `.../related-documents/{addition,division}/relation/{parent-doc,child-doc}/*` | 752 | 934 | 14 | Discarded | additions in 476 records, divisions in 279 |
| `claims/claim/claim-text`, `@num` | 711,547 | 711,547 | 1 | Discarded | no occurrence has text in any record |
| `description/p`, `@num` | 711,547 | 711,547 | 1 | Discarded | no occurrence has text in any record |

Not in the source at all (characterization §3): abstract, CPC codes, citations, family identifier.

## 4. Observations that bear on fidelity

### 4.1 Application reference
47 records (0.007 %) contain more than one `application-reference/document-id`, up to 5. In all 47 the references differ in number and in 16 they also differ in date. The adapter keeps the first in document order and discards the rest. What the additional references denote (related applications, regional data, another structure) is **not determinable** from the census.

### 4.2 Order of IPC entries
The 182,865 records with more than one `classifications-ipcr` container are the usual case, not an exception. In all 708,798 records with IPC entries, `@sequence` is present, unique within the record and ascending in document order across containers. The adapter iterates in document order, so its entry order equals the `sequence` order for every record in this corpus. Downstream the subclasses are a sorted set, so entry order is not part of any current output; an ordinal stored from document order is reproducible. This holds for these 26 files only.

The value pair `(classification-level, classification-value)` is `A|I` in 2,504,351 entries and `A|N` in 113,119; nothing else occurs. Their meaning is the ST36 convention (inventive / additional) and is not verified in this repository.

### 4.3 Priority claims
The adapter keeps one date per claim and discards the claim's country, number and `@kind`. Kinds observed: `international` 555,553, `regional` 39,812, `national` 5,044, `ES` 1,245, `EP` 5, `AR` 1, empty 120 (601,780 claims). Three claims have unreadable dates (anomalies, characterization G7).

### 4.4 Entries the adapter drops
Compared with the `biblio_v1` spike load (an independent consumer of the adapter's output, see ADR 0037 §7): applicant occurrences 803,288 in the source, 803,255 kept (33 without a name); inventor occurrences 1,839,897, 1,839,332 kept (565 without a name); IPC entries 2,617,470 and 2,617,470; priority claims 601,780 and dates kept 601,777. The dropped parties are those for which `_party_names` finds no name (`if name`); whether they carry other data was not examined.

## 5. What this does and does not establish

It establishes which information the current adapter carries and which it does not, with counts. It does **not** establish that discarded fields are unnecessary: their consequence for current or planned uses is unknown unless stated above. Fields absent from this census are absent from these 26 files only. Keeping any discarded field in `biblio_v1` requires a documented change to the adapter and its tests (ADR 0037 §5.2); this inventory authorises none.
