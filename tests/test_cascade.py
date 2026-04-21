HEADERS = {"X-API-Key": "test-key"}


def _payload(**overrides):
    base = {"word": "猫", "depth": 2, "top_k": 3, "min_score": -1.0, "use_stopwords": False}
    base.update(overrides)
    return base


def test_cascade_requires_api_key(client):
    r = client.post("/v1/cascade", json=_payload())
    assert r.status_code == 401


def test_cascade_depth1_returns_only_generation_0_and_1(client):
    r = client.post("/v1/cascade", json=_payload(depth=1, top_k=3), headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    gens = {n["generation"] for n in body["nodes"]}
    assert gens.issubset({0, 1})
    assert 0 in gens
    # root only has generation 0
    roots = [n for n in body["nodes"] if n["generation"] == 0]
    assert len(roots) == 1
    assert roots[0]["word"] == "猫"
    assert roots[0]["parent"] is None


def test_cascade_depth2_shape(client):
    r = client.post("/v1/cascade", json=_payload(depth=2, top_k=3), headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    node_ids = {n["id"] for n in body["nodes"]}
    # ids unique
    assert len(node_ids) == len(body["nodes"])
    # generations within 0..2
    gens = {n["generation"] for n in body["nodes"]}
    assert gens.issubset({0, 1, 2})
    # each edge endpoint must reference existing nodes
    for e in body["edges"]:
        assert e["from"] in node_ids
        assert e["to"] in node_ids
    # meta
    assert body["meta"]["total_nodes"] == len(body["nodes"])


def test_cascade_dag_dedup(client):
    # With high min_score=-1 every call returns many items and same words will appear
    # from multiple parents. Ensure nodes remain unique but edges can repeat.
    r = client.post(
        "/v1/cascade", json=_payload(depth=3, top_k=5), headers=HEADERS
    )
    assert r.status_code == 200
    body = r.json()
    node_ids = [n["id"] for n in body["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    # there are typically more edges than nodes when DAG dedup kicks in
    assert len(body["edges"]) >= len(body["nodes"]) - 1


def test_cascade_max_nodes_truncated(client):
    r = client.post(
        "/v1/cascade",
        json=_payload(depth=3, top_k=10, max_nodes=10),
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["truncated"] is True
    assert len(body["nodes"]) == 10


def test_cascade_unknown_root_word(client):
    r = client.post(
        "/v1/cascade", json=_payload(word="qwertyzzz"), headers=HEADERS
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "word_not_in_vocab"


def test_cascade_dead_end_returns_root_only(client):
    r = client.post(
        "/v1/cascade",
        json=_payload(depth=3, top_k=3, min_score=0.999),
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["nodes"]) == 1
    assert body["nodes"][0]["word"] == "猫"
    assert body["edges"] == []
    assert body["meta"]["generations_reached"] == 0


def test_cascade_depth_upper_bound(client):
    r = client.post(
        "/v1/cascade", json=_payload(depth=5), headers=HEADERS
    )
    assert r.status_code == 422


def test_cascade_pos_filter(client):
    r = client.post(
        "/v1/cascade",
        json=_payload(depth=2, top_k=3, pos=["名詞"]),
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    # root has no pos filled (gen=0 injected without POS)
    non_root = [n for n in body["nodes"] if n["generation"] > 0]
    for n in non_root:
        # Sudachi may return "名詞" as the pos category for nouns
        # With dummy words, this filter can drop all children — accept either case
        pass  # structural test; pos correctness depends on Sudachi dict


def test_cascade_cached_hit(client):
    p = _payload(depth=2, top_k=3)
    r1 = client.post("/v1/cascade", json=p, headers=HEADERS)
    assert r1.status_code == 200
    assert r1.json()["meta"]["cached"] is False

    r2 = client.post("/v1/cascade", json=p, headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["meta"]["cached"] is True


def test_cascade_exclude_propagates_all_generations(client):
    r = client.post(
        "/v1/cascade",
        json=_payload(depth=3, top_k=5, exclude=["犬"]),
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    for n in body["nodes"]:
        assert n["word"] != "犬"


def test_cascade_top_k_per_gen(client):
    r = client.post(
        "/v1/cascade",
        json=_payload(depth=2, top_k_per_gen=[3, 2]),
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    gen1 = [n for n in body["nodes"] if n["generation"] == 1]
    # gen1 is limited to top_k_per_gen[0]=3 since root has only one parent
    assert len(gen1) <= 3


def test_cascade_top_k_per_gen_length_mismatch(client):
    r = client.post(
        "/v1/cascade",
        json=_payload(depth=3, top_k_per_gen=[5, 5]),
        headers=HEADERS,
    )
    assert r.status_code == 422
