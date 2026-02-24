import threading
import time
import requests
import pytest
from func_api import FuncAPI

# --- Setup App for Testing ---

app = FuncAPI(title="Test API")

@app.api("/add", methods=["GET", "POST"])
def add(a: int, b: int) -> int:
    return a + b

@app.api("/secret", methods=["POST"], api_key="test-key")
def secret(msg: str) -> str:
    return f"secret: {msg}"

# Background thread server
def run_server():
    app.run(port=8001)

@pytest.fixture(scope="session", autouse=True)
def test_server():
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(0.5)  # give server time to start
    yield
    # daemon thread will die when pytest exits

# --- Tests ---

def test_info_endpoint():
    res = requests.get("http://127.0.0.1:8001/info").json()
    assert res["success"] is True
    assert res["data"]["title"] == "Test API"
    # /add and /secret should be registered
    assert len(res["data"]["endpoints"]) == 2

def test_get_add():
    res = requests.get("http://127.0.0.1:8001/add?a=10&b=20").json()
    assert res["success"] is True
    assert res["data"] == 30

def test_post_add():
    res = requests.post("http://127.0.0.1:8001/add", json={"a": 5, "b": 15}).json()
    assert res["success"] is True
    assert res["data"] == 20

def test_missing_api_key():
    res = requests.post("http://127.0.0.1:8001/secret", json={"msg": "hello"})
    assert res.status_code == 401
    assert res.json()["success"] is False

def test_valid_api_key():
    res = requests.post(
        "http://127.0.0.1:8001/secret", 
        json={"msg": "hello"}, 
        headers={"X-API-Key": "test-key"}
    )
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["data"] == "secret: hello"
