HEADERS = {"X-API-Key": "test-key"}


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready(client):
    r = client.get("/v1/ready")
    assert r.status_code == 200


def test_metrics_exposed(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


def test_related_requires_api_key(client):
    r = client.get("/v1/related", params={"word": "猫"})
    assert r.status_code == 401


def test_related_ja(client):
    r = client.get(
        "/v1/related",
        params={"word": "猫", "top_k": 3, "min_score": 0.0},
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "猫"
    assert len(body["results"]) <= 3
    assert "猫" not in {x["word"] for x in body["results"]}
    assert "X-Request-Id" in r.headers


def test_related_unknown_word(client):
    r = client.get(
        "/v1/related",
        params={"word": "qwertyzzz"},
        headers=HEADERS,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "word_not_in_vocab"


def test_similarity(client):
    r = client.get(
        "/v1/similarity",
        params={"word1": "猫", "word2": "犬"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert -1.0 <= body["score"] <= 1.0


def test_batch(client):
    payload = {
        "items": [
            {"word": "猫"},
            {"word": "犬"},
            {"word": "qwertyzzz"},
        ],
        "top_k": 2,
        "min_score": 0.0,
    }
    r = client.post("/v1/related/batch", json=payload, headers=HEADERS)
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) == 3
    assert entries[2]["error"] == "word_not_in_vocab"


def test_analogy(client):
    payload = {
        "positive": ["猫", "子猫"],
        "negative": ["犬"],
        "top_k": 3,
        "min_score": 0.0,
    }
    r = client.post("/v1/analogy", json=payload, headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["positive"] == ["猫", "子猫"]
    assert body["negative"] == ["犬"]
    assert len(body["results"]) <= 3
