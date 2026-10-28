# T22, S4 and the partial evidence sheet (#193): decision proposal, draft

**Status:** Draft proposal for the owner's decision. It **decides nothing**: it approves no text, authorises no merge of #193 and no deployment, and changes no ADR, contract or code. The recommendation in §5 is the assistant's. It is separate from the decision on who may see candidates and who may score (E7, a separate proposal), although the two interact (§6).
**Date:** 2026-10-28
**Checks:** [texts proposal](vertical-3-texts-proposal.md) (T22) · [sheet experience proposal](vertical-3-sheet-ux-proposal.md) (S1–S5, blocks) · [E5 evidence specification](vertical-3-e5-evidence-spec.md) · [E5 storage options](vertical-3-e5-storage-options.md) (D4, provisional) · [acceptance record](vertical-3-acceptance-status.md) §4, §8 · [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) E5

## 1. What exists, what does not

* **On `main`:** the data the sheet needs apart from the identifier lists (`documents_by_year`, `configuration`, corpus hashes, the presentation arithmetic of the per-year terms).
* **Draft #193 (not merged):** a **partial** sheet, built locally. It shows blocks 1, 2, 3, 5 and 6 of the reading order of the sheet proposal (what is compared, activity over time with the gap in 2010 labelled, how the expected count arises with its terms and the stored value, where the numbers come from, limits and cautions) and, in block 4, the text **S4**. It is not E5 and is not for exposure.
* **Does not exist:** the full lists of publication identifiers with dates per subclass (D4, required by E5 and contract §5), and any deployment path for them. Their storage is a **provisional** choice (B, outside Git, committed manifest), conditional on a person reading the OEPM legal notice; no one is named for that reading.

## 2. The two texts

| | S4 | T22 |
|---|---|---|
| Wording | «Las listas de identificadores de las subclases aún no están disponibles en esta vista.» | «La lista de identificadores de esta subclase no está disponible. No se muestra la evidencia de actividad.» |
| State it describes | The partial sheet **as a whole** has no identifier lists yet (a state of the product) | In a **complete** E5 sheet, the list of **one** subclass cannot be shown (a runtime state, next to T14, T18 and T19) |
| Where it applies | Only a non-exposed prototype such as #193 | Only once the lists exist and are served |
| Status | **Not approved.** It stands in for T22 | **Not approved.** Its wording and the behaviour of the panel are to be defined after E5 and the deployment of the lists are decided |

They are different states and not two wordings of one. Approving S4 does not approve T22, and the reverse.

## 3. Constraints that do not change with the decision

* The sheet **is** E5 only with the full lists. A partial sheet **must not be exposed**, and a partial result **is never presented as complete** (E5 specification, state list). A visible partial sheet therefore needs a text such as S4, or it would silently omit a block; the alternative to S4 is not a sheet without block 4 but no sheet at all.
* The data file of the pairs stays behind the nginx barrier (404 in the static image), and the sheet depends on it, so today the sheet cannot appear in a deployed image. #187 was merged as an intermediate increment under the same rule.
* S1, S2, S3 and S5 are approved (2026-10-27), subject to the forbidden-words check and M3. The check was run in #193 on the sheet's text and accessible names; M3 is a human reading and is pending.

## 4. Options for #193

| Option | What it means | Advantages | Risks |
|---|---|---|---|
| **1. Approve S4 narrowly and merge #193 as an intermediate increment** | S4 is approved **only** as the text of the non-exposed partial sheet; T22 stays pending. #193 follows the precedent of #187: merged, not E5, not exposed | The sheet becomes a reviewable base on `main`; it allows the visual review and, later, a usability session with synthetic data (the interaction of opening a pair needs it) | More non-E5 code on `main`; the barrier on the data is the only technical guard against exposure; the acceptance record must keep saying «not E5» |
| **2. Keep #193 as a draft; approve neither text** | Nothing changes. Revisit when D4 and E7 are decided | No more intermediate code; nothing to retract | The sheet cannot be used or reviewed from `main`; synthetic-data sessions have no sheet |
| **3. Discard #193 and build the full sheet after D4** | Close #193; reuse its pieces when the lists exist | One finished sheet instead of an intermediate one | Throws away working, tested code; the full sheet is blocked by D4 and by the reading of the OEPM notice, which have no date |
| **4. Merge #193 without any text about block 4** | Not proposed | None | Violates the rule that a partial result is never presented as complete. Listed to be excluded |

## 5. Recommendation

1. **Do not approve T22 now.** It depends on how the lists are stored and served (D4), which is provisional and conditional on the notice reading. Its wording should follow the real states of the delivery (not published, failed to load, integrity failure), and those do not exist yet.
2. **Option 1 or option 2** for S4 and #193; the assistant leans to **option 1** if the owner wants a visual review or a usability session soon, because both need a sheet to open. If neither is planned in the next weeks, **option 2** costs nothing and avoids more intermediate code. This depends on a priority only the owner sets.
3. **In either case**, keep the acceptance record explicit: the sheet is not E5, the lists (D4) and T22 do not exist, and nothing is exposed.
4. **Decide D4 separately**, after a named person reads the OEPM notice (checklist in the repository). It unblocks the full sheet; this proposal does not choose among the storage options.

## 6. Interaction with the E7 decision

The sheet shows data of one pair at a time, but each pair is a candidate: opening it is seeing a candidate. Merging #193 does not expose anything, but **using** it with real data by a person whose role (may score, or may not) is not recorded would break E7. Until E7 is decided, the sheet is used only with synthetic or demonstration data, or by people whose role is already settled.

## 7. Questions the owner must answer

1. S4: approve it narrowly for the non-exposed partial sheet (option 1), or not (options 2 or 3)?
2. If option 1: is a visual review or a usability session planned, so that it is worth merging now?
3. T22: leave it pending until D4 (recommended), or define its wording now?
4. Who reads the OEPM legal notice, and when? Without that, D4 cannot be decided and the full sheet cannot be built.
5. What happens to #193: merge as an increment, keep as a draft, or discard?
