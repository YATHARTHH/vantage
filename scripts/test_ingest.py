import httpx

payload = {
    "project_id": "search-v2",
    "agent_name": "TestSearchAgent",
    "status": "success",
    "model_name": "gpt-4o",
    "tokens_input": 1200,
    "tokens_output": 400,
}

headers = {
    "Content-Type": "application/json",
    "X-API-Key": "dev-local-key",
}

if __name__ == "__main__":
    response = httpx.post("http://localhost:8000/api/v1/ingest/run", json=payload, headers=headers)
    print("Response Status:", response.status_code)
    print("Response Body:", response.json())
