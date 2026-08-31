import pytest


@pytest.mark.asyncio
async def test_create_and_get_project(async_client):
    headers = {"X-API-Key": "dev-local-key"}
    payload = {
        "id": "search-agent-prod",
        "display_name": "Search Agent Production",
        "project_type": "ai_llm",
        "owner_team": "ai-search",
        "owner_email": "search@company.com",
        "description": "Production LLM search agent",
        "log_prompts": True,
    }

    response = await async_client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "search-agent-prod"
    assert data["log_prompts"] is True

    # Get project
    get_res = await async_client.get("/api/v1/projects/search-agent-prod")
    assert get_res.status_code == 200
    assert get_res.json()["display_name"] == "Search Agent Production"


@pytest.mark.asyncio
async def test_add_source_mapping(async_client):
    headers = {"X-API-Key": "dev-local-key"}
    proj_payload = {
        "id": "chat-assistant",
        "display_name": "Chat Assistant",
        "project_type": "ai_llm",
        "owner_team": "chat-team",
        "owner_email": "chat@company.com",
    }
    await async_client.post("/api/v1/projects", json=proj_payload, headers=headers)

    mapping_payload = {
        "source_tool": "langfuse",
        "source_identifier": "chat-prod-v1",
        "display_label": "LangFuse Production Trace",
    }
    map_res = await async_client.post(
        "/api/v1/projects/chat-assistant/mappings", json=mapping_payload, headers=headers
    )
    assert map_res.status_code == 201
    map_data = map_res.json()
    assert map_data["project_id"] == "chat-assistant"
    assert map_data["source_tool"] == "langfuse"


@pytest.mark.asyncio
async def test_ui_projects_page(async_client):
    res = await async_client.get("/")
    assert res.status_code == 200
