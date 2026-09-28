"""
Unit tests for Phase 1 foundations: BioHttpClient, disk cache, bio schemas, and /api/bio/health.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from backend.api.bio_schemas import (
    ProteinRecord,
    SequenceFormat,
    SequenceRecord,
    SequenceType,
    StructureRecord,
    ValidationResult,
)
from backend.config import Settings
from backend.main import app
from backend.utils.error_types import (
    DatabaseAuthError,
    DatabaseClientError,
    DatabaseNotFoundError,
    DatabaseRateLimitError,
)
from backend.utils.http_client import BioHttpClient, DiskCache, RateLimiter


@pytest.fixture
def temp_cache_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_disk_cache_roundtrip(temp_cache_dir):
    cache = DiskCache(cache_dir=temp_cache_dir)
    assert cache.get("test:key") is None

    cache.set("test:key", '{"result": "mammoth"}', ttl_seconds=60)
    cached = cache.get("test:key")
    assert cached is not None
    assert json.loads(cached) == {"result": "mammoth"}


def test_disk_cache_expiry(temp_cache_dir):
    cache = DiskCache(cache_dir=temp_cache_dir)
    cache.set("test:short", "val", ttl_seconds=-1)  # expired immediately
    assert cache.get("test:short") is None


def test_rate_limiter_throttles():
    limiter = RateLimiter()
    limiter.set_delay("test.host", 0.05)
    t0 = time.time()
    limiter.wait("https://test.host/api/1")
    limiter.wait("https://test.host/api/2")
    elapsed = time.time() - t0
    assert elapsed >= 0.04


@respx.mock
def test_bio_http_client_ncbi_params_and_headers(temp_cache_dir):
    settings = Settings(
        ncbi_email="researcher@paleo.edu",
        ncbi_api_key="mock-key-123",
        bio_cache_dir=temp_cache_dir,
    )
    client = BioHttpClient(settings=settings)

    route = respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").respond(
        status_code=200, json={"result": "ok"}
    )

    resp = client.request("GET", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", params={"db": "nuccore"})
    assert resp.status_code == 200
    assert route.called
    last_req = route.calls.last.request
    assert "email=researcher%40paleo.edu" in str(last_req.url)
    assert "tool=PaleoRAG" in str(last_req.url)
    assert "api_key=mock-key-123" in str(last_req.url)
    assert "PaleoRAG" in last_req.headers["user-agent"]


@respx.mock
def test_bio_http_client_caching(temp_cache_dir):
    settings = Settings(bio_cache_dir=temp_cache_dir)
    client = BioHttpClient(settings=settings)

    route = respx.get("https://rest.uniprot.org/uniprotkb/D3U1H9.json").respond(
        status_code=200, json={"primaryAccession": "D3U1H9"}
    )

    r1 = client.get_json("https://rest.uniprot.org/uniprotkb/D3U1H9.json")
    assert r1["primaryAccession"] == "D3U1H9"
    assert route.call_count == 1

    # Second call should be served from cache with no second HTTP call
    r2 = client.get_json("https://rest.uniprot.org/uniprotkb/D3U1H9.json")
    assert r2["primaryAccession"] == "D3U1H9"
    assert route.call_count == 1


@respx.mock
def test_bio_http_client_error_handling(temp_cache_dir):
    settings = Settings(bio_cache_dir=temp_cache_dir)
    client = BioHttpClient(settings=settings)

    respx.get("https://rest.uniprot.org/uniprotkb/MISSING.json").respond(status_code=404)
    with pytest.raises(DatabaseNotFoundError):
        client.request("GET", "https://rest.uniprot.org/uniprotkb/MISSING.json", use_cache=False)

    respx.get("https://rest.uniprot.org/uniprotkb/UNAUTH.json").respond(status_code=401)
    with pytest.raises(DatabaseAuthError):
        client.request("GET", "https://rest.uniprot.org/uniprotkb/UNAUTH.json", use_cache=False)


def test_bio_schemas_validation():
    seq = SequenceRecord(
        id="HQ184444.1",
        name="Mammoth_HBB",
        sequence="ATGGTGCACCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTG",
        length=57,
        seq_type=SequenceType.dna,
        gc_content=59.65,
    )
    assert seq.id == "HQ184444.1"
    assert seq.length == 57

    prot = ProteinRecord(
        accession="D3U1H9",
        entry_name="D3U1H9_MAMPR",
        protein_name="Hemoglobin subunit beta",
        organism="Mammuthus primigenius",
        organism_id=37349,
        sequence="MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH",
        length=147,
    )
    assert prot.accession == "D3U1H9"
    assert prot.length == 147

    struct = StructureRecord(
        pdb_id="3VRF",
        title="Crystal structure of ancestral woolly mammoth hemoglobin",
        resolution_angstrom=1.55,
        method="X-ray diffraction",
        cath_codes=["1.10.490.10"],
        cath_names=["Globins"],
    )
    assert struct.pdb_id == "3VRF"
    assert struct.cath_codes == ["1.10.490.10"]


@respx.mock
def test_bio_health_endpoint():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi").respond(status_code=200, text="<einfo/>")
    respx.get("https://rest.uniprot.org/uniprotkb/P02100.json").respond(status_code=200, json={})
    respx.get("https://data.rcsb.org/rest/v1/core/entry/2A07").respond(status_code=200, json={})
    respx.get("https://string-db.org/api/json/version").respond(status_code=200, json={})

    client = TestClient(app)
    resp = client.get("/api/bio/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "services" in data
