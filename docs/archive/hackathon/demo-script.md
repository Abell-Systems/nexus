# Demo Video Script — IP Matchmaker

**Duration:** ~4 minutes (Live / Unedited Action Flow)  
**Track:** The Taskmaster (Devpost "All Things Agentic Hackathon")  
**Locked Domain:** *"Solid-state electrolytes for EV batteries"*  

---

## Timed Video Script (4:00 Total)

```text
0:00–0:30  Problema & Context
0:30–1:00  Input & Problem Formulation
1:00–1:40  Landscape Mining & White-Space Detection
1:40–2:30  Agent Working (Research & Inventor Proposal)
2:30–3:40  Adversarial Rejection Loop & Traceable Evidence
3:40–4:00  Cloud Run & Google Cloud Live Infrastructure Proof
```

---

## Breakdown & Voiceover Guide

### 0:00 – 0:30 | Problema (Problem Statement)
- **Visual:** Split screen: Massive, dense patent database listings vs. R&D teams searching manually for freedom-to-operate white spaces.
- **Voiceover:**
  > "Finding genuine, patentable white-space opportunities is like finding a needle in a haystack. Traditional keyword search tools return thousands of dense patents, leaving researchers to manually guess prior-art risks."

### 0:30 – 1:00 | Input (Domain Selection)
- **Visual:** User inputs query *"solid-state electrolytes"* and domain *"EV batteries"* in the IP Matchmaker UI.
- **Voiceover:**
  > "Meet IP Matchmaker: an autonomous R&D intelligence agent built on Google ADK, Gemini 3.5, and Google Cloud BigQuery. We start by specifying a technical domain—solid-state electrolytes for EV batteries—combining supply-side patents with a market-demand signal."

### 1:00 – 1:40 | Landscape + White-Space
- **Visual:** The execution view shows the pipeline stages advancing live. Highlight the white-space cluster ("Solid Electrolytes - Sulfide & Oxide Interfaces") and its `white_space_score` once results land.
- **Voiceover:**
  > "Our landscape engine mines Google Patents Public Datasets on BigQuery, groups patents by CPC classification, and calculates a quantitative white-space score combining density, recency, citation velocity, and market demand. Clusters highlighted in green reveal true innovation white spaces."

### 1:40 – 2:30 | Agent Working
- **Visual:** Clicking "Analyze White Space" triggers `POST /api/analyze`. Status changes to `running`. The **Inventor Agent** generates `InventionCandidate` (candidate_id: `c1-inv-1`).
- **Voiceover:**
  > "When a white space is selected, IP Matchmaker launches an autonomous multi-agent pipeline. Our **Inventor Agent** analyzes the cluster and proposes a novel candidate invention: a gradient sulfide-halide solid electrolyte interface to prevent dendrite growth."

### 2:30 – 3:40 | Adversarial Rejection Loop & Traceable Evidence
- **Visual:** In the AGENT ACTIVITY FEED, follow the real-time exchange: **Inventor Agent** proposes a candidate, **Adversarial Agent** challenges it citing specific prior-art publication numbers pulled live from BigQuery, and emits a `"rejected"` verdict with rationale. The **Inventor Agent** ingests that rejection and proposes a refined candidate. Let this repeat once or twice live.
- **Voiceover:**
  > "Here's what makes this more than a chatbot: our **Adversarial Agent** doesn't just critique — it searches real prior art on BigQuery and cites specific patent numbers to justify every rejection. When it rejects a proposal, the **Inventor Agent** reads that exact citation and comes back with a genuinely different approach. Every claim on screen right now is backed by a real publication number, not an LLM guess — that's the traceability this system is built around, whether a candidate ultimately survives adversarial scrutiny or not."

*(Note: whether the final candidate survives or is rejected after all iterations, the evidence trail above — real cited prior art driving each rejection and revision — is the point being demonstrated, not a specific outcome.)*

### 3:40 – 4:00 | Cloud Run / Google Cloud Proof
- **Visual:** Browser showing live backend URL on Cloud Run (`https://patent-agent-...run.app/health`) and Google Cloud Console dashboard with active Cloud Run service logs.
- **Voiceover:**
  > "IP Matchmaker runs live on Google Cloud Run, leveraging Gemini 3.5 and BigQuery. This is autonomous innovation intelligence ready for production. Thank you!"

---

## Recording Golden Rules

1. **Unedited Action:** Show actual agent responses and UI state transitions without skipping steps.
2. **Cloud Run Visibility:** Keep Google Cloud Console / Cloud Run URL visible on screen at the 3:40 mark to fulfill GCP proof criteria.
