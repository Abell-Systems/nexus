import os

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-used-by-wiring-checks")

from patent_agent.agent import invention_loop, root_agent
from patent_agent.sub_agents.adversarial.agent import adversarial_agent
from patent_agent.sub_agents.governor.agent import governor_agent
from patent_agent.sub_agents.inventor.agent import inventor_agent
from patent_agent.sub_agents.research.agent import research_agent


def test_root_agent_pipeline_order():
    names = [agent.name for agent in root_agent.sub_agents]
    assert names == ["research_agent", "invention_loop", "governor_agent"]


def test_invention_loop_contains_inventor_and_adversarial():
    names = [agent.name for agent in invention_loop.sub_agents]
    assert names == ["inventor_agent", "adversarial_agent"]


def test_research_agent_has_patent_tools():
    tool_names = {getattr(t, "__name__", getattr(t, "name", None)) for t in research_agent.tools}
    assert "search_patents_tool" in tool_names
    assert "get_similar_patents_tool" in tool_names
    assert "get_citations_tool" in tool_names
    assert "cluster_patents_tool" in tool_names


def test_adversarial_agent_has_exit_loop_tool():
    tool_names = {getattr(t, "__name__", getattr(t, "name", None)) for t in adversarial_agent.tools}
    assert "exit_loop" in tool_names


def test_all_agents_have_output_keys():
    assert research_agent.output_key == "patent_landscape"
    assert inventor_agent.output_key == "candidate_inventions"
    assert adversarial_agent.output_key == "adversarial_verdicts"
    assert governor_agent.output_key == "scored_candidates"
