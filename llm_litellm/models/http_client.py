import json
import requests
from requests.exceptions import RequestException

class LiteLLMClient:
    """HTTP client for LiteLLM proxy"""
    def __init__(self, api_key, api_base=None):
        self.api_key = api_key
        self.api_base = api_base or "http://localhost:4000"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def _make_request(self, method, endpoint, data=None, stream=False, **kwargs):
        """Make HTTP request to LiteLLM proxy"""
        url = f"{self.api_base}{endpoint}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data if data else None,
                stream=stream,
                **kwargs
            )
            response.raise_for_status()
            return response
        except RequestException as e:
            error_msg = str(e)
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_msg = error_data["error"].get("message", str(e))
            except (AttributeError, ValueError, json.JSONDecodeError):
                pass
            raise Exception(f"LiteLLM API error: {error_msg}") from e

    def chat_completion(self, messages, model, stream=False):
        """Create chat completion"""
        data = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        response = self._make_request("POST", "/chat/completions", data=data, stream=stream)

        if not stream:
            return response.json()
        else:
            for line in response.iter_lines():
                if line:
                    if line.startswith(b"data: "):
                        line = line[6:]  # Remove "data: " prefix
                    if line.strip() == b"[DONE]":
                        break
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    def create_embeddings(self, texts, model):
        """Create embeddings"""
        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]

        data = {
            "model": model,
            "input": texts
        }
        response = self._make_request("POST", "/embeddings", data=data)
        return response.json()

    def list_models(self):
        """List available models"""
        response = self._make_request("GET", "/models")
        return response.json()
