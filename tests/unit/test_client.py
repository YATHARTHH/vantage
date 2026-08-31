import pytest
from vantage.client import vantage

def test_vantage_track_agent_decorator():
    @vantage.track_agent(project_id="search-v2", model_name="gpt-4o", tokens_input=100, tokens_output=50)
    def dummy_agent(query: str):
        return f"result for {query}"

    res = dummy_agent("test query")
    assert res == "result for test query"
