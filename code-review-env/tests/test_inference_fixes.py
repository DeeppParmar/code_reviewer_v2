import pytest
from unittest.mock import MagicMock
import httpx
import inference

def test_success_true_when_score_above_threshold(monkeypatch, capsys):
    # Mock environment server and openai
    mock_client = MagicMock()
    mock_post = MagicMock()
    
    def fake_post(url, json=None, timeout=None):
        resp = MagicMock()
        resp.raise_for_status = lambda: None
        if "reset" in url:
            resp.json.return_value = {"max_steps": 2}
        else:
            # step
            operation = json.get("operation")
            if operation == "done":
                resp.json.return_value = {
                    "observation": {}, "reward": 0.99, "done": True, 
                    "info": {"current_score": 0.40}
                }
            else:
                resp.json.return_value = {
                    "observation": {}, "reward": 0.20, "done": False, 
                    "info": {"current_score": 0.20}
                }
        return resp
    
    mock_post.side_effect = fake_post
    mock_client.post = mock_post
    
    class FakeContext:
        def __enter__(self): return mock_client
        def __exit__(self, *args): pass
        
    monkeypatch.setattr(httpx, "Client", lambda: FakeContext())
    
    mock_llm = MagicMock()
    mock_create = MagicMock()
    mock_create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content='{"operation": "add_comment", "line_number": 1, "severity": "minor", "category": "bug", "message": "issue"}'))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content='{"operation": "done"}'))])
    ]
    mock_llm.chat.completions.create = mock_create
    monkeypatch.setattr(inference, "OpenAI", lambda **kwargs: mock_llm)
    
    # Run
    inference.run_task("easy", env_base_url="fake", api_base_url="fake", model_name="fake", hf_token="fake", timeout_s=10)
    
    # Check
    captured = capsys.readouterr()
    assert "[END] success=true" in captured.out

def test_success_false_when_invalid_model(monkeypatch, capsys):
    class FakeContext:
        def __enter__(self): 
            c = MagicMock()
            c.post.return_value.json.return_value = {"max_steps": 2}
            return c
        def __exit__(self, *args): pass
        
    monkeypatch.setattr(httpx, "Client", lambda: FakeContext())
    
    def mock_raise(**kwargs):
        raise Exception("Error code: 400 - Invalid model")
        
    mock_llm = MagicMock()
    mock_llm.chat.completions.create = mock_raise
    monkeypatch.setattr(inference, "OpenAI", lambda **kwargs: mock_llm)
    
    # Run
    inference.run_task("easy", env_base_url="fake", api_base_url="fake", model_name="fake", hf_token="fake", timeout_s=10)
    
    # Check
    captured = capsys.readouterr()
    assert "[END] success=false" in captured.out

def test_llm_mode_calls_api_not_deterministic_fallback(monkeypatch):
    monkeypatch.setenv("REVIEW_STRATEGY", "llm")
    action = inference._get_benchmark_action("hard", 1)
    assert action is None

def test_hard_task_system_prompt_contains_no_line_numbers():
    prompt = inference.load_system_prompt()
    lines = ["line 23", "line 28", "line 34", "line 40", "line 18", "line 26"]
    for l in lines:
        assert l not in prompt.lower()
