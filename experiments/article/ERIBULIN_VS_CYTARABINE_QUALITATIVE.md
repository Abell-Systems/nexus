# Qualitative inspection: Eribulin mesylate's 8 relevant families vs. Cytarabine's 123

Follow-up to `SCIENTIFIC_INTERPRETATION.md` (§2), per the reviewer's
suggested next step. Source: `screening_table_consolidated.csv`
(tag `paper-data-milestone-2026-09-22`, unchanged). No new data acquired —
this reads only the Evidence text and application-type flags already
recorded during classification.

**Question.** Does Eribulin mesylate's higher observed relevance rate
(44.4%, 8/18, vs. Cytarabine's 17.8%, 123/690 — flagged as an exploratory,
not confirmatory, finding in `SCIENTIFIC_INTERPRETATION.md` §2) correspond
to a recognizable technological/application pattern, or mainly reflect the
composition of the two search universes?

## 1. Application-type profile: two different populations of "relevant"

| Application flag | Cytarabine (n=123) | Eribulin mesylate (n=8) |
|---|---:|---:|
| Therapeutic Application | 76.4% (94) | 37.5% (3) |
| Combination Therapy | 67.5% (83) | 25.0% (2) |
| Manufacturing | 3.3% (4) | **50.0% (4)** |
| Chemical Modification | 8.1% (10) | **37.5% (3)** |
| Formulation | 8.1% (10) | 25.0% (2) |
| Drug Delivery | 7.3% (9) | 37.5% (3) |
| Diagnostic Application | 1.6% (2) | 12.5% (1) |
| Conjugation | 1.6% (2) | 0.0% (0) |

**Relevance-class split is also different**: Cytarabine's 123 relevant
families split 69 Directly Relevant / 54 Indirectly Relevant (44% Indirect).
Eribulin's 8 are **100% Directly Relevant, 0% Indirectly Relevant**.

## 2. Reading the evidence text: what these families are actually about

**Cytarabine's Indirectly Relevant families (54/123, the largest single
bucket)** are almost entirely inventions about something *else* — a
different antibody, a nanoparticle platform, an MDM2 inhibitor, a novel
kinase modulator — whose claims name cytarabine as one option in a short,
structured combination-partner list (typically 5–8 named drugs), or invoke
a named standard-of-care regimen that includes it. Representative examples
from the evidence text:

- "A structured multi-part combination claim narrows the 'anti-metabolite'
  component to a short 5-item list (5-fluorouracil, methotrexate,
  gemcitabine, cytarabine, fludarabine)..." (HK-1220412-A1)
- "The description explicitly names the specific fixed 'ADE' combination
  regimen (Cytarabine, Daunorubicin Hydrochloride, Etoposide) as a
  chemotherapy combinable with CD123-CAR T-cell immunotherapy..." (IL-298332-A)
- "Claims Compound 1 combined with one or more antitumor agents selected
  from a specific 8-item list (cisplatin, oxaliplatin, 5-FU, gemcitabine,
  cytarabine, SN-38, irinotecan, docetaxel)..." (HK-1154344-A1)

**Cytarabine's Directly Relevant families (69/123)** follow a similar
pattern one level up: cytarabine specifically named (not just among a short
list) as the combination partner, delivery-vehicle payload, or dosing
subject — but the *invention itself* is usually still about something else
(a nanoparticle platform, an MDM2-p53 inhibitor, an antibody), with
cytarabine cast as the established AML/leukemia standard-of-care drug being
combined with or delivered alongside it:

- "Claim 1 is explicitly a two-component pharmaceutical product of an
  MDM2-p53 inhibitor and cytarabine for AML treatment..." (CA-2926307-C)
- "Claim 6 specifically claims the antineoplastic agent as 'daunorubicin
  combined with cytarabine', one of only two specific named combinations..."
  (EP-3272350-B1)
- "Claim 28 and the description repeatedly discuss cytarabine as a
  specifically named, central example anticancer active principle for the
  claimed stealth lipid nanocapsule / liposomal drug-delivery invention..."
  (IN-2004DN03885-A)

**Eribulin's 8 Directly Relevant families**, by contrast, are dominated by
patents where eribulin (or eribulin mesylate) *is* the invention's subject,
not a named option within someone else's invention:

- 3 of 8: **synthesis/manufacturing process patents** for eribulin itself
  (a macrocyclization reaction, synthetic intermediates ER811475/ER076349) —
  IN-349478-B, US-10865212-B2, IN-201647018392-A.
- 3 of 8: **liposomal formulation patents** with eribulin as the claimed
  payload — US-20210177802-A1, US-20190111022-A1, AU-2014200717-A1.
- 2 of 8: **specific combination-therapy claims naming eribulin explicitly**
  as one of exactly two named agents (not a short list) — "Use of eribulin
  and lenvatinib as combination therapy" (CA-2915005-C); eribulin + PD-1
  antagonist (US-20210177802-A1, also counted under formulation above).
- 1 of 8: a **biomarker/diagnostic patent** for predicting eribulin
  treatment response (US-20140235707-A1).

**Eribulin's Incidental Mentions (10/18)** follow the same generic-list
mechanism as Cytarabine's Incidentals — eribulin named as one of ~15–20
items in an unrelated invention's background chemotherapy-agent list (e.g.
three sibling "kinase modulation compounds" families reusing the identical
~20-item list, an anti-LAG3-antibody patent, a TIM-3-binding antibody
patent). This confirms the *mechanism* that produces Incidental Mentions is
the same for both compounds — what differs is how often each compound's
screened universe lands in that bucket versus the others.

## 3. What this does and doesn't support

**Supports a real structural difference, not just noise:** Cytarabine's
relevant families are overwhelmingly *combination-partner* mentions inside
other inventors' patents (Combination Therapy 67.5% vs. Eribulin's 25.0%;
44% Indirectly Relevant vs. 0%), consistent with its role as a decades-old,
generically-available component of established chemotherapy regimens
(the evidence text itself surfaces named regimens like "ADE" and repeated
"cytarabine + anthracycline" claim patterns). Eribulin's relevant families
are overwhelmingly about eribulin *itself* — its synthesis (Manufacturing
50% vs. 3.3%; Chemical Modification 37.5% vs. 8.1%) and its formulation —
consistent with a compound whose patent activity centers on protecting or
extending IP around the molecule rather than on other inventors reusing it
as a routine combination partner.

**Does not establish, and would need data this analysis doesn't have:**
whether this reflects Eribulin's more specific/less generic compound name
(fewer accidental Markush-list hits for reasons of *nomenclature* alone,
independent of its actual regimen usage), a genuine difference in real-world
combination-regimen adoption, or assignee concentration (e.g. whether
Eribulin's Directly Relevant patents cluster under a small number of
assignees around the originating company, vs. Cytarabine's being spread
across many unrelated assignees) — assignee identity is not a field in the
current classification (`screening_table_consolidated.csv` has no assignee
column; Table 5 in the manuscript, which does have assignee data, comes
from the separate, unrelated Espacenet dataset and cannot be joined to this
table). Confirming the assignee-concentration hypothesis would require a
new, explicitly-scoped data acquisition — not done here, consistent with
the standing decision not to pull new data in response to this finding.

**Sample size caveat carries over from `SCIENTIFIC_INTERPRETATION.md`:**
Eribulin's n=8 relevant / n=18 screened remains small. The qualitative
pattern above describes what these specific 8 families are about — it is
descriptive of the observed sample, not a claim that it generalizes beyond
it.
