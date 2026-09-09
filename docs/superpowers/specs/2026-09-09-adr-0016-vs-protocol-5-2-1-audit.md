# Audit: ADR 0016 vs. Protocol §5.2.1 — Is an a priori BM25 min-max defensible?

**Status:** Investigation only. No code, ADR, or protocol change. Branch: `feat/adr-0016-fusion-normalization`.
**Question being answered:** Can BM25 min-max scaling, as protocol §5.2.1 literally specifies it, be defined with bounds fixed a priori — independent of the benchmark, reproducible, and scientifically defensible? Only if the answer is no does `x/(x+k)` get evaluated (not done in this pass).

---

## 1. What §5.2.1 literally requires

Exact protocol text (`docs/empirical-study-protocol.md` §5.2, item 1):

> **Lexical Scoring ($S_{\text{lex}}$):** Okapi BM25 ($k_1 = 1.5, b = 0.75$) computed over Spanish-stemmed unigrams/bigrams, normalized via min-max scaling **across $\mathcal{P}_{\text{shared}}(d)$** to $[0, 1]$.

The scope is explicit and easy to miss: **min-max is computed per demand $d$, across that demand's own shared candidate pool** — not across the full patent corpus $\mathcal{P}$, and not across the benchmark/dataset as a whole. For each $d$: $S_{\text{lex}}^{\text{norm}}(d,p) = \frac{S_{\text{lex}}(d,p) - \min_{p' \in \mathcal{P}_{\text{shared}}(d)} S_{\text{lex}}(d,p')}{\max_{p' \in \mathcal{P}_{\text{shared}}(d)} S_{\text{lex}}(d,p') - \min_{p' \in \mathcal{P}_{\text{shared}}(d)} S_{\text{lex}}(d,p')}$.

Two things the protocol leaves unspecified that matter here:
- What happens when all candidates in $\mathcal{P}_{\text{shared}}(d)$ have the same BM25 score (degenerate: $\max = \min$, division by zero) — not addressed in §5.2.1's text.
- Nothing about *where the min/max come from* beyond "across $\mathcal{P}_{\text{shared}}(d)$" — this is unambiguous once read carefully, but easy to misread as "across the corpus" or "across the benchmark," which is a different, much larger scope.

## 2. Contrast with ADR 0012's actual prohibition

ADR 0016 rejects "Min-max normalization of BM25" citing: *"the bounds are either derived from this benchmark's own score distribution (contamination) or from an arbitrarily assumed corpus size that won't match the eventual large dataset."*

This objection targets a **global** min-max — bounds computed once, across the whole benchmark or corpus, and then reused. That is a real ADR 0012 violation if true: fitting a normalization to the sealed 45-pair (or 39-demand) benchmark and then evaluating that same benchmark with it is textbook post-hoc calibration on the only test set this system will ever have.

**But that is not what §5.2.1 actually specifies.** Per-demand, pool-scoped min-max recomputes its own min/max fresh for every single demand, using only that demand's own retrieved candidates — never any benchmark-wide or corpus-wide statistic. It is not "fit" on anything: it is a deterministic function applied identically at Dev time, Test time, and any future deployment, with no parameter carried over between demands or estimated from held-out data. In that specific sense, **the protocol's literal min-max does not commit ADR 0012's violation** — there is no benchmark-derived parameter here to leak.

**Finding 1:** ADR 0016's stated rejection reason for min-max (constraints 1/5 — contamination, non-portability) does not accurately describe protocol §5.2.1's literal per-demand-scoped specification. It describes a *different, global* reading of "min-max" that the protocol doesn't actually prescribe.

## 3. The three candidate bound sources, evaluated

### 3a. Theoretical bounds (from BM25's own definition)
BM25's minimum is well-defined: $0$, when a candidate shares no scored terms with the query (already the case ADR 0016 itself treats as meaningful signal — "no lexical evidence"). But BM25 has **no fixed theoretical maximum** — its ceiling depends on term frequencies, document length normalization, and IDF, which depends on the reference corpus's term-frequency distribution. This is exactly ADR 0016's own correct observation about "Corpus-statistics-based normalization." **A parameter-free theoretical max does not exist for BM25** the way it does for cosine similarity ($[-1,1]$, exact by definition). This path is closed regardless of scope (global or per-demand).

### 3b. Fixed a priori bounds (chosen before the experiment, independent of any data)
In principle one could declare, say, "BM25 scores above 20 are treated as 1.0" as a fixed prior, the same way $f_{\text{lex}}$'s $k=1.0$ is declared a prior rather than calibrated. This would satisfy ADR 0012 (no benchmark-derived parameter) and would be reproducible. But it inherits **exactly the same justification burden ADR 0016 already places on $k=1.0$**: the chosen ceiling is an arbitrary scale decision with no more principled grounding than $k=1.0$'s "simplest unit-scale prior" framing — it isn't obviously *more* defensible than the rational transform, it's a structurally identical kind of guess, just wearing a "min-max" label. This option doesn't privilege min-max over $x/(x+k)$; it just relocates the same open question (what's the right BM25 scale?) into a different functional form.

### 3c. Corpus-derived bounds, frozen before the test set is touched (Dev-fit, Test-applied)
The standard ML pattern (fit a scaler on Dev, freeze it, apply unchanged to Test) would satisfy ADR 0012 — the parameter comes from Dev, not from the sealed Test set, so no contamination. **This path is currently blocked structurally**, independent of its scientific merits: the traceability audit (§3A of `docs/paper/manuscript-outline.md`) already found the Dev/Test split does not exist anywhere in code. There is no Dev set to fit bounds on yet. This option cannot be evaluated as "defensible today" — it's contingent on work that hasn't happened.

### 3d. What the protocol actually specifies: per-demand pool-scoped bounds (§1 above)
Not really "theoretical," "fixed a priori," or "Dev-frozen" — a fourth category the audit's original three-way framing didn't name explicitly: bounds computed **fresh per demand, from that demand's own retrieved pool, at evaluation time**. Reproducible (deterministic given the same pool) and immune to ADR 0012 contamination (no benchmark-wide statistic involved) — Finding 1 already established that. Its problem lies elsewhere:

## 4. Where per-demand min-max actually fails — not contamination, but ADR 0016's constraint (4)

`ConfidenceThresholds` (`domain/models/matching.py:445-448`) are confirmed **fixed, global, single-instance constants** — `config/policies/matching/default_matching_policy.json`: `strong=0.7, moderate=0.4, weak=0.1`, one policy file, applied identically to every demand's `overall_score` regardless of which pool it came from. This is ADR 0016's own constraint (4): *"Any transform whose output depends on the pool it's computed within... would make a fixed threshold mean something different per demand."*

Per-demand min-max is, by construction, exactly this failure mode: the same raw BM25 value normalizes to a different $S_{\text{lex}}^{\text{norm}}$ depending entirely on what else happens to be in that demand's retrieved pool. A demand whose pool is uniformly weak lexical matches gets its best (still-weak) candidate stretched to $1.0$; a demand whose pool contains one dominant lexical match compresses everything else toward $0$. Two demands with identical raw BM25 evidence for a given patent can produce completely different normalized scores and therefore different `strong`/`moderate`/`weak` classifications for the same underlying evidence. This is the identical failure ADR 0016 already used to reject "rank-based/softmax normalization within the closed candidate pool" — **per-demand min-max belongs in that rejected category, not in the "global min-max" category ADR 0016 actually argued against.**

Two additional, protocol-text-level problems, independent of the above:
- **Degenerate case unaddressed:** §5.2.1 doesn't say what happens when $\max = \min$ within $\mathcal{P}_{\text{shared}}(d)$ (division by zero) — a real, not hypothetical, case for any demand whose entire pool has identical or zero BM25 scores.
- **Interpretability across demands breaks by design:** a "$1.0$" lexical score means "the best-matching candidate in *this* demand's pool," not any fixed absolute notion of lexical strength — which is a coherent choice for some purposes (e.g., ranking within one demand) but incompatible with cross-demand comparability, which the frozen `ConfidenceThresholds` require.

## 5. Where this leaves the decision (not concluded — per the agreed order, $x/(x+k)$ not evaluated yet)

- **3a (theoretical bounds):** closed — doesn't exist for BM25.
- **3b (fixed a priori bounds):** open in principle, but inherits the identical justification burden as $k$ — doesn't obviously beat the rational transform, just relocates the same question.
- **3c (Dev-frozen corpus bounds):** structurally blocked today — no Dev/Test split exists to fit on.
- **3d (protocol's actual per-demand min-max):** reproducible and ADR-0012-clean, but **fails ADR 0016's own constraint (4)** — the correct reason to reject it, not the contamination reason ADR 0016 currently states.

**Net finding:** protocol §5.2.1's min-max, read literally and precisely, is not vulnerable to the objection ADR 0016 raises against it — but it is vulnerable to a different, real objection (pool-dependence breaking fixed global thresholds) that ADR 0016 also already articulates, just not pointed at this specific target. Before any acceptance/amendment decision: **ADR 0016's own rejection table needs a correction** (min-max's actual failure mode, per the protocol's real scope, is constraint 4 — not constraints 1/5) even if the final verdict (reject min-max) turns out the same. Getting the *reason* right matters here, since a future reader checking whether a "fixed a priori bounds" variant of min-max (3b) could rescue it would reach a different, wrong conclusion if they only read ADR 0016's current (mistargeted) argument.

## 6. Second pass — is there a corpus-independent, a priori BM25 bound applicable uniformly across demands?

Sharpened question: can a **global** (not per-demand) BM25 normalization exist that simultaneously (a) preserves `ConfidenceThresholds`' absolute, cross-demand interpretation, (b) is reproducible and untouched by the benchmark's relevance labels, and (c) actually produces a well-utilized, interpretable $[0,1]$ scale? Two candidate forms, both derived without inspecting §5.2.1 further — this is new analysis.

### 6a. A priori upper-bound construction based only on corpus size and query length

Okapi BM25's per-term contribution is bounded above by $\text{idf}(\text{term}) \cdot (k_1+1)$ as $\text{tf} \to \infty$ ($b$ can only reduce it, never increase it). Without inspecting any real term-frequency statistic, $\text{idf}$'s own supremum is achieved by the rarest a term could possibly be — appearing in exactly one document ($n=1$) — giving $\text{idf}_{\max}(N) = \ln\!\left(\frac{N - 1 + 0.5}{1 + 0.5} + 1\right) \approx \ln(N/1.5)$. A fully a priori ceiling for demand $d$ with $L_d$ stemmed query terms: $\text{BM25}_{\text{ceiling}}(d) = L_d \cdot \text{idf}_{\max}(N) \cdot (k_1+1)$ — computed from $N$ (corpus size, known once $\mathcal{P}$ is frozen), $L_d$ (the demand's own query length, known from its text), and $k_1$ (fixed constant). **No candidate score, no relevance grade, no benchmark statistic enters this formula.**

**Correction from initial framing:** this is *not* a single global bound in the sense (a) needs. Because $\text{BM25}_{\text{ceiling}}(d)$ scales linearly with $L_d$, it is demand-dependent by construction — two demands with different query lengths get different ceilings, so it does not supply one fixed number comparable across demands the way `ConfidenceThresholds` requires. It is better described as a **corpus-independent functional upper bound, applied uniformly (same formula, same inputs-only-known-in-advance) across demands** — uniform in *procedure*, not in *value*. It satisfies (b) cleanly (reproducible, untouched by annotated data) but **does not satisfy (a) as stated** — a further reason, distinct from (c), that this construction does not rescue global min-max. Set that aside and check (c) anyway, since it's independently informative: the ceiling assumes every query term is simultaneously as rare as a term can possibly be ($n=1$ in a corpus of up to 50,000) *and* saturating ($\text{tf}\to\infty$) — real BM25 scores for genuine (demand, patent) matches will sit orders of magnitude below this ceiling, so even a demand-length-adjusted version of it would compress virtually all real evidence into a narrow sliver near $0$. **Fails on two independent grounds, not one.**

### 6b. Arbitrary global fixed constant (not derived from BM25's own math)

E.g., declaring "BM25 scores above 15 map to 1.0" without deriving 15 from anything. This one *is* demand-independent, satisfying (a) genuinely, and satisfies (b) trivially — but it is exactly the earlier-identified path 3b, restated: **exactly as unprincipled as $k=1.0$**, no smaller justification burden, no structural advantage. Choosing this over $x/(x+k)$ would not be "preferring min-max," it would be picking the same category of arbitrary-prior decision under a different name.

### Answer

Neither 6a nor 6b is a viable rescue for global min-max — but for different reasons, and the claim should be stated at the strength the evidence actually supports, not stronger. 6a fails (a) outright (it's demand-dependent, not a genuine single global bound) and independently fails (c). 6b satisfies (a) and (b) but is exactly as arbitrary as the transform it would replace. **This pass did not find a global a priori BM25 bound that additionally satisfies (c) with a non-arbitrary justification** — that is a statement about what this investigation located, not a claim that no such construction can mathematically exist ("scientifically defensible" is not a provable property; absence of a finding is not proof of impossibility). The practical conclusion for this audit is the same either way: neither candidate is currently usable.

## 7. Where this leaves ADR 0016's verdict (still not modifying ADR 0016, protocol, or code)

**ADR 0016's ultimate decision (reject min-max) survives this two-pass audit — but its stated justification does not, and needs revision before formal acceptance:**
- Min-max **as the protocol literally specifies it** (per-demand, pool-scoped, §1/§4 above) fails ADR 0016's own constraint (4) — breaks `ConfidenceThresholds`' absolute cross-demand meaning — not the contamination/non-portability reasons (constraints 1/5) ADR 0016's table currently states.
- Min-max **in any global a priori form** (§6 above) either fails to produce a usable $[0,1]$ scale (6a) or is exactly as arbitrary as $k=1.0$ (6b) — so it doesn't survive as a rescued alternative either, but not for the reason currently written down.
- **Net:** ADR 0016 reached approximately the right conclusion through an argument that doesn't hold for the specific thing it was arguing against. Before formally accepting ADR 0016 (moving it from `Proposed` to `Accepted`) or amending the protocol on its authority, the rejection table for min-max should be corrected to state the real reason — otherwise a future reader re-litigating this question (e.g., re-examining 3b/6b) would be misled by an argument that doesn't actually apply to what they're checking.

**Cleared to proceed, per the agreed order:** evaluating $x/(x+k)$ — starting with $k=1.0$ — as an independent scientific decision, not as an automatic consequence of rejecting min-max.

---

## 8. Evaluating $x/(x+k)$, $k=1.0$ — four questions, in order

Discipline maintained throughout: no code touched, no pilot run, **no relevance label or benchmark score inspected to pick $k$** — everything below is derived from BM25's own fixed constants ($k_1=1.5$, $b=0.75$, already committed to independent of this question) and its formula, or from ADR 0015's already-published distributional diagnostic (median/p75 of raw BM25 $=0$ across the pilot — a property of the *raw feature*, not of any relevance judgment, so citing it doesn't reintroduce ADR 0012 contamination).

### 8.1 What property does the lexical signal actually need?

Being in $[0,1)$ is necessary but not sufficient. For $f_{\text{lex}}$ to be fit for its role in $S_{\text{hybrid}} = \alpha f_{\text{lex}} + \beta f_{\text{sem}} + \gamma f_{\text{cpc}}$:
1. **Order-preserving (strictly monotonic).** Any two candidates' raw BM25 ranking must survive the transform unchanged — a ranking signal that scrambles order is worse than useless.
2. **$f(0)=0$.** Already established (§ADR 0016 context) — "no shared terms" must stay "zero contribution," not become manufactured moderate signal.
3. **Bounded, never clamped.** Established already — a clamp destroys ordering among high scorers; $x/(x+k)$ satisfies this by construction (asymptotic, never reaches 1).
4. **Demand-independence (does not reintroduce §3A's constraint-4 problem).** Unlike per-demand min-max, $f_{\text{lex}}$ must depend only on the candidate's own raw score, not on what else is in that demand's pool — otherwise `ConfidenceThresholds`' absolute, cross-demand meaning breaks again, for the same reason §4 rejected min-max.
5. **Resolving power should sit where the real data actually lives.** Given BM25's own documented distribution (median $=0$, p75 $=0$ across the pilot — most pairs share no scored terms at all), a transform that spends most of its $[0,1]$ range on values that almost never occur, while compressing the region where most *non-zero* real scores actually fall, would waste the scale's discriminative power exactly where discrimination matters most.

$x/(x+k)$ satisfies 1-4 by construction, for any $k>0$ — this is not new (ADR 0016 already establishes monotonicity and boundedness). Criterion 5 is where the choice of $k$ actually matters, and is not addressed by ADR 0016's text.

### 8.2 What does $f(x) = x/(x+1)$ actually do to BM25?

Mathematically, for $k=1$: $f$ is strictly increasing ($f'(x) = 1/(x+1)^2 > 0$), concave for $x>0$ ($f''(x) = -2/(x+1)^3 < 0$), $f(0)=0$, $f(x) \to 1$ as $x\to\infty$, and $f(1)=0.5$ (the crossing point). Concavity means **equal raw differences produce a larger $\Delta f$ near $x=0$ than near large $x$** — the transform's resolving power is concentrated in the low range and compressed in the high range. Combined with 8.1's criterion 5 (real data concentrated near $0$), this concentration is *directionally* correct — the transform is more sensitive exactly where most real pairs sit. Whether it is *correctly calibrated* (not just correctly shaped) depends entirely on where $k$ places the $0.5$-crossing relative to that real distribution — which is exactly §8.3's question.

**Fusion-comparability note (new, not previously flagged):** $f_{\text{sem}}(x) = (x+1)/2$ is an *exact affine* remap of cosine — a unit change in raw cosine always means the same thing in $f_{\text{sem}}$, everywhere in its range. $f_{\text{lex}}$ is *saturating* — a unit change in raw BM25 means very different things depending on where you are on the curve. $f_{\text{cpc}}$ is an untransformed 5-value discrete tier. The three fused signals therefore have structurally different "unit meanings" before $\alpha/\beta/\gamma$ ever get applied — not necessarily wrong (asymmetric signal treatment is common and often appropriate in heterogeneous-feature fusion), but a real asymmetry worth stating explicitly in Methods rather than presenting $S_{\text{hybrid}}$ as a symmetric weighted average of comparable quantities.

### 8.3 Why exactly $k=1.0$? (the decisive question)

ADR 0016 frames $k=1.0$ as "the simplest possible scale in BM25's own raw units" — a neutral, parameter-minimal prior. **This claim is checkable against the algorithm's own fixed constants, and does not hold up.**

Using the repo's committed $k_1=1.5$, $b=0.75$ and the standard Okapi BM25 per-term formula, a **single occurrence of one query term at average document length** contributes almost exactly $\text{idf}(\text{term})$ to the raw score (the $\text{tf}$/length-normalization factor reduces to $\approx 1$ at $\text{tf}=1$, average length — verified numerically, not assumed). Computing $\text{idf}(N=50{,}000, n)$ for a range of term document-frequencies and passing through $f(x)=x/(x+1)$:

| Term's document frequency | Raw BM25 (1 occurrence) | $f(\text{raw})$ |
|---|---|---|
| 1 (appears in 1 patent) | 10.41 | 0.912 |
| 500 (1% of corpus) | 4.60 | 0.822 |
| 2,500 (5% of corpus) | 3.00 | 0.750 |
| 12,500 (25% of corpus) | 1.39 | **0.581** |
| 25,000 (50% of corpus) | 0.69 | 0.409 |

**Finding:** a single shared term that appears in as many as **25% of a 50,000-record corpus** — a relatively common term, by document-frequency alone, no semantic-relevance interpretation implied — already pushes $f_{\text{lex}}$ past $0.5$ with just *one* occurrence, before any other evidence is considered. A term present in 5% or fewer of patents pushes $f_{\text{lex}}$ above $0.75$ from a single occurrence. This directly conflicts with ADR 0015's own diagnostic that the *raw* distribution is dominated by zeros (median/p75 $=0$): under $k=1.0$, the jump from "zero shared terms" to "one shared, relatively common term" is not a small step up from a near-zero baseline — it's most of the way to the ceiling.

**Answering the four sub-options directly:**
- *Does $k=1.0$ have a defensible scale interpretation?* It has a **stated** one ("BM25's own raw units"), but that unit is not neutral — BM25 raw scores are not naturally scaled to any fixed, corpus-independent reference; "$1.0$" in BM25's own units, given $k_1=1.5$, corresponds to roughly "one occurrence of a term shared by a quarter of the entire corpus." That is not an intuitively "minimal" amount of lexical evidence to define as the half-signal point.
- *Is it simply an arbitrary constant?* Not entirely arbitrary in form (it's the simplest value of a one-parameter family, and ADR 0016 is honest that it's a declared prior, not a fit) — but its **numeric consequence**, once worked out against the algorithm's own fixed constants, does not match the "neutral/minimal" framing given to it. The arbitrariness is real; it's just been under-examined, not mis-stated as something it explicitly isn't.
- *Does a less arbitrary $k$ exist?* Possibly — $k$ could be derived from BM25's own term-frequency statistics (e.g., the corpus's median/typical single-term score) **without touching any relevance judgment**, which would be corpus-derived but not benchmark(-label)-contaminated in ADR 0012's actual sense (analogous to how IDF itself is already a corpus statistic, not considered "contamination" in the IR literature). This has not been done and is a legitimate next step if $k=1.0$ is rejected — not attempted here, since doing so would require inspecting real corpus term-frequency statistics that don't exist yet (no live `PatentCorpus`).
- *Should $k$ be Dev-tuned?* Structurally possible in principle (add $k$ as a fourth parameter to protocol §5.2.4/§8.1's existing Dev cross-validation alongside $\alpha,\beta,\gamma$) but **currently blocked** by the same missing-Dev/Test-split finding as everything else in this audit trail (§3A of `docs/paper/manuscript-outline.md`) — cannot be executed today regardless of the scientific merits.

### 8.4 Consequences for the experimental design

Two live paths, not resolved here (that's the ADR-acceptance decision, still pending):
1. **Keep $k$ fixed a priori, but not at the current, unexamined $1.0$.** Requires re-deriving a genuinely minimal/neutral crossing point from BM25's own math (e.g., solving for the $k$ at which a single occurrence of a very common term — say, top-decile document frequency — lands near some small, explicitly justified target such as $f\approx 0.1$-$0.2$, not $\approx 0.5$-$0.9$). Stays a zero-hyperparameter-tuning design, consistent with ADR 0016's original intent, but the value itself needs re-justifying, not just re-asserting.
2. **Promote $k$ to a Dev-tuned hyperparameter**, alongside $\alpha,\beta,\gamma$. ADR-0012-compliant *if and only if* it's fit exclusively on Dev and frozen before Test — but this widens the tuning search space (a new axis, potential interaction effects with $\alpha,\beta,\gamma$) and requires an explicit protocol amendment naming $k$ as a tuned parameter, not just a stated constant. Blocked today by the missing Dev/Test split regardless.

Neither path was chosen here — this is the required input for that decision, not the decision itself. **What this session's audit changes concretely:** $k=1.0$ cannot be carried into an Accepted ADR 0016 or into Methods prose as "a neutral, self-evidently minimal prior" — the numbers above show it isn't one, under the algorithm's own already-committed constants. Both min-max (§1-7) and the current $k=1.0$ (§8) need a revision before ADR 0016 is ready to accept — this audit does not conclude the fusion-normalization question, it narrows it to a real, well-defined re-derivation task.

## 9. Identification pass — does a defensible, non-arbitrary $k$ exist?

Decisive question, per the agreed framing: *does a definition of $k$ based exclusively on BM25 exist, with a clear interpretation and a reasonably-used scale, that isn't just "the number we happen to like"?* Evaluated as three distinct families, deliberately not picked between yet.

### 9.1 Family 1 — pure BM25 structural math, no corpus statistics at all

Checked directly: does BM25's formula contain any quantity that is a fixed, corpus-independent number — the way cosine similarity's $[-1,1]$ range is fixed by the dot-product definition alone, independent of any corpus?

**No.** Every quantity in BM25 that could serve as a reference scale runs through $\text{idf}$, and $\text{idf}(N,n) = \ln\!\left(\frac{N-n+0.5}{n+0.5}+1\right)$ is, by construction, a function of the corpus's own document-frequency statistics ($N$, $n$) — there is no idf value, and therefore no BM25 raw-score value, that exists independent of some corpus. $k_1$ and $b$ (already fixed at $1.5$/$0.75$) govern *shape* (tf-saturation, length normalization) — relative behavior — not an absolute scale; they cannot supply a numeric $k$ on their own, only a functional form for how one would apply once chosen.

**This is not a new failure — it is the same structural fact §3a and §6a already established for BM25's theoretical maximum, now shown to apply symmetrically to BM25's theoretical "half-signal" point.** BM25 is corpus-relative by design (that is precisely what idf is for); nothing about its formula alone, in isolation from any corpus, fixes a scale. **Family 1 is a dead end — not because no one has found the right formula yet, but because the quantity being sought (a corpus-independent BM25 reference point) does not exist under Okapi BM25's own definition.**

### 9.2 Family 2 — corpus statistics, no relevance labels

Conceptually sound in principle (idf itself is already a corpus statistic and is not, by IR convention, considered "benchmark contamination" under anything like ADR 0012's actual rule, which targets fitting to *labeled outcomes*, not corpus term-frequency structure). But **scope is everything here**, and two variants must be told apart:

- **Bad variant — pool/demand-relative statistic** (e.g., "$k$ = median BM25 score within each demand's own retrieved pool"): this silently resurrects §4's exact failure. A statistic computed per-demand from that demand's own pool makes $f_{\text{lex}}$ depend on what else got retrieved for that specific demand — the identical constraint-4 violation that sank per-demand min-max. **Rejected on the same grounds, not evaluated further.**
- **Viable variant — a single, global, demand-blind statistic of $\mathcal{P}$ itself**, frozen the moment $\mathcal{P}$ is frozen, before any demand is ever paired against it, before any Dev/Test split, before any relevance label exists. Candidate definition: $k$ = a percentile (e.g., median) of $\mathcal{P}$'s own vocabulary idf distribution — i.e., $\text{idf}(N, n_t)$ computed over every distinct term $t$ appearing in $\mathcal{P}$'s corpus, using each term's real document frequency $n_t$ within $\mathcal{P}$ — **no query, no demand, no pairing, no label enters this computation at all.** This is structurally the same kind of object idf itself already is (a corpus vocabulary statistic), just aggregated into a single scalar and reused as the fusion transform's scale parameter instead of as a per-term weight.

This variant would satisfy: **(a) demand-blind** (computed before any demand exists in the computation), **(b) label-blind** (never touches a relevance grade), **(c) globally consistent** (one number, applied identically everywhere — preserves `ConfidenceThresholds`' absolute meaning, unlike per-demand min-max), **(d) reproducible from a frozen, hashed artifact** ($\mathcal{P}$'s own vocabulary, once frozen) rather than from this study's own outcomes. It is **not** available today: it requires $\mathcal{P}$ to actually exist (still blocked — PR-E0.2), and the exact statistic (which percentile, term-frequency threshold for "vocabulary" inclusion, stemming/tokenization consistency with the retriever's own) needs its own precise specification before computing anything — not attempted here, since doing so on a corpus that doesn't exist yet would itself be premature.

### 9.3 Family 3 — Dev-tuned hyperparameter

Already characterized in §8.4 — scientifically clean *if and only if* fit exclusively on Dev, frozen before Test, and requires (i) the Dev/Test split to exist (currently missing entirely, §3A) and (ii) an explicit protocol amendment naming $k$ as a tuned parameter alongside $\alpha,\beta,\gamma$ (protocol §5.2.4/§8.1 currently name only those three). Not blocked by anything *conceptually* new — blocked by the same missing infrastructure as everything else downstream of the Dev/Test gap.

### 9.4 Answer to the decisive question

**Family 1 is closed — not weak, closed: no corpus-independent BM25 reference scale exists, by the same structural fact that already closed the theoretical-bounds question for min-max.** Family 2 has a genuinely defensible, demand-blind, label-blind variant (§9.2's viable form) — but it cannot be computed until $\mathcal{P}$ exists, and its exact statistic still needs precise specification once it does. Family 3 is clean in principle but currently blocked by the missing Dev/Test split, same as several other findings in this audit trail.

**This supports exactly the framing the user proposed:** the functional form ($x/(x+k)$, monotonic, $f(0)=0$, demand-independent) can reasonably be fixed a priori — §8.1-8.2 found no structural objection to the *shape*. Its **scale ($k$'s specific value) cannot currently be fixed a priori with a defensible, non-arbitrary justification** — $k=1.0$ fails that bar (§8.3), and the one family that could supply a principled a priori scale (§9.2's viable variant) is not computable yet. Until $\mathcal{P}$ exists and §9.2 is either computed and found reasonable, or a properly Dev-gated §9.3 tuning is implemented, **no value of $k$ currently has a defensible justification** — including $1.0$. This is a genuine open question, not a preference between three equally good options — flagged here, not resolved.

**No ADR, protocol, or code touched in this pass**, per the agreed discipline.
