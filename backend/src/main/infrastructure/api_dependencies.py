"""Shared runtime singletons for the Cloud Run FastAPI app.

Split out of api.py so infrastructure/analysis_pipeline.py (job orchestration) and
infrastructure/api.py (routes) can both depend on the agent runner, datasources, and
job store without importing each other.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402

from application.research_service import ResearchService  # noqa: E402
from infrastructure.adk.agent import build_invention_pipeline  # noqa: E402
from infrastructure.llm.provider_policy import (  # noqa: E402
    ProviderPacingPlugin,
    get_execution_policy,
)
from infrastructure.sources.bigquery_patents import get_patents_datasource  # noqa: E402
from infrastructure.sources.demand_sources import get_demand_datasource  # noqa: E402
from infrastructure.storage.job_store import get_job_store  # noqa: E402

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

_rate_limiter = ProviderPacingPlugin()
_execution_policy = get_execution_policy()
_session_service = InMemorySessionService()

_root_agent = build_invention_pipeline()

_runner = Runner(
    agent=_root_agent,
    app_name="ip_matchmaker",
    session_service=_session_service,
    plugins=[_rate_limiter],
)

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    allow_origins=_ORIGINS,
    web=False,
)

_patents_datasource = get_patents_datasource()
_demand_datasource = get_demand_datasource()
_research_service = ResearchService(
    patents_datasource=_patents_datasource,
    demand_datasource=_demand_datasource,
)
_job_store = get_job_store()
