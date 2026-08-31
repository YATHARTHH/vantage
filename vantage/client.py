import functools
import time
import httpx
from typing import Optional, Callable

class VantageClient:
    def __init__(self, endpoint: str = "http://localhost:8000", api_key: str = "dev-local-key"):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    def track_agent(
        self,
        project_id: str,
        agent_name: Optional[str] = None,
        model_name: str = "gpt-4o",
        tokens_input: int = 500,
        tokens_output: int = 200,
    ) -> Callable:
        """
        Decorator to auto-instrument Python AI agent functions and stream telemetry to Vantage.
        
        Example:
            @vantage.track_agent(project_id="search-v2", model_name="gpt-4o")
            def run_search_agent(query: str):
                return "search results..."
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "success"
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    status = "error"
                    raise e
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    payload = {
                        "project_id": project_id,
                        "agent_name": agent_name or func.__name__,
                        "status": status,
                        "model_name": model_name,
                        "tokens_input": tokens_input,
                        "tokens_output": tokens_output,
                    }
                    try:
                        httpx.post(
                            f"{self.endpoint}/api/v1/ingest/run",
                            json=payload,
                            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                            timeout=2.0
                        )
                    except Exception:
                        pass
            return wrapper
        return decorator

vantage = VantageClient()
