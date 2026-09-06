import json


def test_chat_stream_requires_auth(client):
    response = client.post("/api/chat/stream", json={"query": "test question"})
    assert response.status_code == 401


def test_chat_stream_returns_streamed_answer_with_no_hallucinated_citations(client, auth_headers, test_vector_store):
    # Seed the store with a chunk whose doc_id matches the mock LLM's canned citation.
    test_vector_store.upsert_chunks(
        [
            {
                "id": "seed::0",
                "dense_vector": [0.1] * 768,
                "payload": {
                    "doc_id": "seed",
                    "chunk_index": 0,
                    "section": "Results",
                    "chunk_type": "text",
                    "chunk_text": "Relevant paleogenomic evidence.",
                    "content_hash": "h0",
                },
            }
        ]
    )

    response = client.post("/api/chat/stream", json={"query": "What evidence exists?"}, headers=auth_headers)
    assert response.status_code == 200

    events = [line for line in response.text.split("\n\n") if line.startswith("data: ")]
    final_event = json.loads(events[-1][len("data: "):])

    assert final_event["done"] is True
    assert final_event["citation_warnings"] == []


def test_chat_stream_flags_hallucinated_citation_when_chunk_not_retrieved(client, auth_headers):
    # No chunks seeded in the store -> the mock LLM's [seed:0] citation is hallucinated.
    response = client.post("/api/chat/stream", json={"query": "What evidence exists?"}, headers=auth_headers)
    final_event = json.loads(
        [line for line in response.text.split("\n\n") if line.startswith("data: ")][-1][len("data: "):]
    )

    assert len(final_event["citation_warnings"]) == 1


def test_upload_rejects_unapproved_source(client, auth_headers):
    response = client.post(
        "/api/upload",
        params={"source": "not_a_real_source"},
        files={"file": ("test.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 422  # enum validation failure from FastAPI/pydantic


def test_upload_requires_auth(client):
    response = client.post("/api/upload", files={"file": ("test.pdf", b"content", "application/pdf")})
    assert response.status_code == 401


def test_health_endpoint_is_reachable_without_auth(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "qdrant_ok" in body


def test_ingest_endpoint_requires_auth(client):
    response = client.post("/api/ingest", json={"source": "pmc_oa", "doi_or_url": "PMC12345678"})
    assert response.status_code == 401


def test_ingest_endpoint_enqueues_task(client, auth_headers):
    response = client.post("/api/ingest", json={"source": "pmc_oa", "doi_or_url": "PMC99999999"}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "task_id" in body
    assert body["status"] == "queued"


def test_task_status_endpoint(client, auth_headers):
    response = client.get("/api/task/unsubmitted_test123", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "unsubmitted_test123"
    assert body["state"] == "PENDING"

