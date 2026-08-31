"""Single source of truth for session.state keys shared across agents.

Keep docs/architecture.md's "Shared state table" in sync with this file.
"""

PATENT_LANDSCAPE = "patent_landscape"  # produced by research_agent
SELECTED_CLUSTER_CONTEXT = "selected_cluster_context"  # compact context for one cluster, seeded by main.py (see tools/context.py)
CANDIDATE_INVENTIONS = "candidate_inventions"  # produced by inventor_agent
ADVERSARIAL_VERDICTS = "adversarial_verdicts"  # produced by adversarial_agent
SCORED_CANDIDATES = "scored_candidates"  # produced by governor_agent
