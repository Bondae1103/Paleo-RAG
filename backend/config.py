"""
Centralized configuration for PaleoRAG.

All settings are read from environment variables (see .env.example).
Nothing here should require values to be hardcoded — every tunable knob
called out in the implementation plan (embedding model name, LLM provider,
reranker flag, etc.) lives here.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- API ---
    api_bearer_token: str = "changeme-dev-token"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "paleo_chunks"
    # If true, use an in-memory/embedded Qdrant instance instead of a server.
    # Useful for local dev and tests; NOT for production ingestion at scale.
    qdrant_use_local_mode: bool = False
    qdrant_local_path: str = "./data/qdrant_storage"

    # --- Embeddings ---
    # Swappable without touching calling code, per the implementation plan's
    # requirement that PubMedBERT vs. general-purpose embeddings be A/B-able.
    embedding_model_name: str = "NeuML/pubmedbert-base-embeddings"
    embedding_dimension: int = 768
    embedding_batch_size: int = 32

    # --- Sparse retrieval ---
    # "qdrant_native" uses Qdrant's built-in sparse vectors; "rank_bm25" uses
    # an in-process BM25 index. See DECISIONS.md for which is active and why.
    sparse_retrieval_backend: str = "rank_bm25"

    # --- Reranking (optional stretch goal, must exist as a flag either way) ---
    reranker_enabled: bool = False
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- LLM ---
    llm_provider: str = "ollama"  # "ollama" | "anthropic" | "mock"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # --- Taxonomy resolution ---
    gbif_api_base: str = "https://api.gbif.org/v1"
    pbdb_api_base: str = "https://paleobiodb.org/data1.2"
    taxonomy_cache_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 days
    query_expansion_enabled: bool = True

    # --- Ingestion sources ---
    pmc_oa_service_base: str = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
    biorxiv_api_base: str = "https://api.biorxiv.org"

    # --- Biological Database APIs ---
    ncbi_eutils_base: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    ncbi_api_key: str = ""
    ncbi_email: str = "paleorag@example.edu"
    ena_api_base: str = "https://www.ebi.ac.uk/ena/portal/api"
    uniprot_api_base: str = "https://rest.uniprot.org"
    rcsb_api_base: str = "https://data.rcsb.org/rest/v1"
    interpro_api_base: str = "https://www.ebi.ac.uk/interpro/api"
    prosite_api_base: str = "https://prosite.expasy.org"
    string_api_base: str = "https://string-db.org/api"
    biogrid_api_base: str = "https://webservice.thebiogrid.org"
    biogrid_api_key: str = ""
    kegg_api_base: str = "https://rest.kegg.jp"
    ensembl_api_base: str = "https://rest.ensembl.org"
    bio_cache_dir: str = "./data/bio_cache"
    bio_cache_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days

    # --- Chunking ---
    chunk_target_tokens: int = 512
    chunk_overlap_tokens: int = 50
    chunk_hard_cap_tokens: int = 1024

    # --- Retrieval ---
    retrieval_top_k: int = 8

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
