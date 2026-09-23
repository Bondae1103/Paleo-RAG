/**
 * PaleoRAG API Client
 * Manages communication with the FastAPI backend, supporting both relative
 * proxying (local dev) and direct origin queries via VITE_API_URL (Vercel deployment).
 */

export interface SearchFilters {
  taxon_scientific_name?: string;
  geological_period?: string;
  publication_year_min?: number;
  publication_year_max?: number;
}

export interface RetrievedChunk {
  doc_id: string;
  chunk_index: number;
  section: string;
  chunk_type: "text" | "table" | "caption" | string;
  score: number;
  text: string;
}

export interface CitationWarning {
  cited_marker: string;
  reason: string;
}

export interface ChatStreamTerminalPayload {
  done: boolean;
  retrieved_chunks: RetrievedChunk[];
  citation_warnings: CitationWarning[];
}

export interface HealthResponse {
  status: "ok" | "degraded";
  qdrant_ok: boolean;
  redis_ok: boolean;
  llm_ok: boolean;
  detail: {
    llm_provider?: string;
    ollama_models?: string[];
    qdrant_error?: string | null;
    redis_error?: string | null;
    ollama_error?: string | null;
    anthropic_error?: string | null;
  };
}

export interface TaskStatusResponse {
  task_id: string;
  state: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  error?: string | null;
  result?: {
    doc_id?: string;
    upserted?: number;
    [key: string]: unknown;
  } | null;
}

export interface ManifestDocument {
  doc_id: string;
  source: string;
  license: string;
  doi: string;
  title: string;
  retrieved_at: string;
  raw_path: string;
  status: string;
}

const DEFAULT_TOKEN = "sk-paleorag-8f2c9a1e";

export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === "string") {
    return envUrl.replace(/\/+$/, "");
  }
  return "";
}

export function getBearerToken(): string {
  const stored = localStorage.getItem("paleorag-token");
  if (stored) return stored;
  const envToken = import.meta.env.VITE_API_BEARER_TOKEN;
  if (envToken && typeof envToken === "string") return envToken;
  return DEFAULT_TOKEN;
}

export function setBearerToken(token: string): void {
  localStorage.setItem("paleorag-token", token);
}

function authHeaders(): Record<string, string> {
  const token = getBearerToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Check backend health status
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const base = getApiBaseUrl();
  const resp = await fetch(`${base}/api/health`, {
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    throw new Error(`Health check returned HTTP ${resp.status}`);
  }
  return resp.json();
}

/**
 * Stream conversational answers with phylogenetic grounding and citation auditing
 */
export async function streamChatQuery({
  query,
  filters,
  topK = 8,
  onToken,
  onDone,
  onError,
  signal,
}: {
  query: string;
  filters?: SearchFilters;
  topK?: number;
  onToken: (token: string) => void;
  onDone: (terminal: ChatStreamTerminalPayload) => void;
  onError: (error: Error) => void;
  signal?: AbortSignal;
}): Promise<void> {
  const base = getApiBaseUrl();
  const payload = {
    query,
    filters: filters || null,
    top_k: topK,
  };

  try {
    const response = await fetch(`${base}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication failed: invalid or missing API_BEARER_TOKEN.");
      }
      const errText = await response.text();
      throw new Error(`Server returned HTTP ${response.status}: ${errText}`);
    }

    if (!response.body) {
      throw new Error("No readable stream received in response body.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const block of lines) {
        const trimmed = block.trim();
        if (!trimmed.startsWith("data:")) continue;
        const jsonStr = trimmed.slice(5).trim();
        if (!jsonStr) continue;

        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed.token !== undefined) {
            onToken(parsed.token);
          }
          if (parsed.done === true) {
            onDone(parsed as ChatStreamTerminalPayload);
          }
        } catch (parseErr) {
          console.warn("Failed to parse SSE event:", jsonStr, parseErr);
        }
      }
    }
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      return;
    }
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

/**
 * Upload manual PDF paper
 */
export async function uploadPdfDocument(file: File): Promise<{ task_id: string; status: string }> {
  const base = getApiBaseUrl();
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${base}/api/upload?source=manual_upload`, {
    method: "POST",
    headers: {
      ...authHeaders(),
    },
    body: formData,
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Upload failed (${response.status}): ${err}`);
  }

  return response.json();
}

/**
 * Trigger remote ingestion for PMC OA accession or bioRxiv DOI
 */
export async function ingestRemoteDocument(
  doiOrUrl: string,
  source: "pmc_oa" | "biorxiv" | "manual_upload" = "pmc_oa"
): Promise<{ task_id: string; status: string }> {
  const base = getApiBaseUrl();
  const response = await fetch(`${base}/api/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({
      doi_or_url: doiOrUrl,
      source: source,
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Remote ingestion failed (${response.status}): ${err}`);
  }

  return response.json();
}

/**
 * Poll task execution status
 */
export async function fetchTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const base = getApiBaseUrl();
  const response = await fetch(`${base}/api/task/${encodeURIComponent(taskId)}`, {
    headers: {
      ...authHeaders(),
    },
  });

  if (!response.ok) {
    throw new Error(`Task query failed (${response.status})`);
  }

  return response.json();
}

/**
 * Retrieve indexed literature documents
 */
export async function fetchDocuments(): Promise<{ documents: ManifestDocument[]; total: number }> {
  const base = getApiBaseUrl();
  const response = await fetch(`${base}/api/documents`, {
    headers: {
      ...authHeaders(),
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch documents (${response.status})`);
  }

  return response.json();
}

/**
 * Retrieve evaluation benchmark statistics
 */
export async function fetchEvalSummary(): Promise<{
  metrics: {
    recall_at_5: number;
    recall_at_10: number;
    citation_faithfulness: number;
    hallucinated_citations: number;
    embedding_model: string;
    total_questions: number;
  };
  golden_questions: Array<{
    question: string;
    expected_source_doc_ids: string[];
    expected_answer_contains: string[];
  }>;
}> {
  const base = getApiBaseUrl();
  const response = await fetch(`${base}/api/eval/summary`, {
    headers: {
      ...authHeaders(),
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch evaluation summary (${response.status})`);
  }

  return response.json();
}
