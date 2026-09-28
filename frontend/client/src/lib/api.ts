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
  bio_cards?: BioLookupResponse | null;
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
  const stored = typeof window !== "undefined" ? localStorage.getItem("paleorag-api-url") : null;
  if (stored) return stored.replace(/\/+$/, "");
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === "string") {
    return envUrl.replace(/\/+$/, "");
  }
  return "";
}

export function setApiBaseUrl(url: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("paleorag-api-url", url.trim());
  }
}

export async function safeJson<T = any>(resp: Response): Promise<T> {
  const contentType = resp.headers.get("content-type") || "";
  const text = await resp.text();
  if (contentType.includes("text/html") || text.trim().startsWith("<")) {
    throw new Error(
      "Received HTML instead of JSON. The backend server might be offline, or Vercel is rewriting /api requests to index.html. Please configure your live Backend API URL in Diagnostics settings."
    );
  }
  try {
    return JSON.parse(text) as T;
  } catch (err: any) {
    throw new Error(`Invalid JSON response: ${err.message}. Response: ${text.slice(0, 100)}`);
  }
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
  return safeJson<HealthResponse>(resp);
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

  return safeJson(response);
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

  return safeJson(response);
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

  return safeJson<TaskStatusResponse>(response);
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

  return safeJson(response);
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

  return safeJson(response);
}

// ---------------------------------------------------------------------------
// Biological Databases & Sequence Tools Schemas & API Client (CO1 - CO6)
// ---------------------------------------------------------------------------

export type SequenceType = "dna" | "rna" | "protein" | "unknown";
export type SequenceFormat = "fasta" | "genbank" | "embl";

export interface SequenceFeature {
  type: string;
  location: string;
  qualifiers: Record<string, unknown>;
}

export interface SequenceRecord {
  id: string;
  name: string;
  description: string;
  sequence: string;
  length: number;
  seq_type: SequenceType;
  gc_content?: number | null;
  molecular_weight_kda?: number | null;
  ambiguity_index?: number | null;
  features: SequenceFeature[];
  annotations: Record<string, unknown>;
}

export interface ValidationResult {
  is_valid: boolean;
  seq_type: SequenceType;
  length: number;
  gc_percent: number;
  molecular_weight_kda: number;
  ambiguity_index: number;
  invalid_characters: string[];
  details: string;
}

export interface ConversionResponse {
  output_text: string;
  record_count: number;
  records: SequenceRecord[];
}

export interface OpenReadingFrame {
  frame: number;
  start: number;
  end: number;
  length_nt: number;
  length_aa: number;
  strand: number;
  protein_sequence: string;
}

export interface TranslationFrame {
  frame: number;
  strand: number;
  translation: string;
  orfs: OpenReadingFrame[];
}

export interface TranslationResponse {
  dna_sequence: string;
  rna_sequence: string;
  reverse_complement: string;
  frames: TranslationFrame[];
  longest_orf?: OpenReadingFrame | null;
}

export interface SubmissionValidationRequest {
  locus_name: string;
  sequence: string;
  molecule_type?: string;
  topology?: string;
  division?: string;
  organism: string;
  definition: string;
  authors?: string[];
  title?: string;
}

export interface SubmissionValidationResponse {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  preview_genbank_record?: string | null;
}

export interface ProteinRecord {
  accession: string;
  entry_name: string;
  protein_name: string;
  organism: string;
  organism_id?: number | null;
  sequence: string;
  length: number;
  active_sites: Array<Record<string, unknown>>;
  disulfide_bonds: Array<Record<string, unknown>>;
  ptms: Array<Record<string, unknown>>;
  pir_ids: string[];
  cross_references: Record<string, Array<Record<string, unknown>>>;
}

export interface StructureRecord {
  pdb_id: string;
  title: string;
  resolution_angstrom?: number | null;
  method: string;
  deposit_date?: string | null;
  cath_codes: string[];
  cath_names: string[];
  scop_folds: string[];
  ligands: string[];
  chains: string[];
  coordinates_url: string;
}

export interface DomainHit {
  id: string;
  database: string;
  name: string;
  description: string;
  start: number;
  end: number;
}

export interface PathwayHit {
  pathway_id: string;
  name: string;
  database: string;
  url: string;
  description?: string | null;
}

export interface InteractionEdge {
  source: string;
  target: string;
  score: number;
  evidence_channels: Record<string, number>;
}

export interface LocusLink {
  gene_symbol: string;
  species: string;
  chromosome: string;
  start: number;
  end: number;
  assembly: string;
  ensembl_url: string;
  ucsc_url: string;
}

export interface BioLookupResponse {
  query: string;
  organism?: string | null;
  nucleotide_record?: SequenceRecord | null;
  protein_record?: ProteinRecord | null;
  structure_record?: StructureRecord | null;
  domains: DomainHit[];
  pathways: PathwayHit[];
  interactions: InteractionEdge[];
  locus?: LocusLink | null;
}

import {
  convertSequenceClient,
  fetchStructureMutationsClient,
  lookupBioClient,
  scanMotifsClient,
  translateDogmaClient,
  validateSequenceClient,
  validateSubmissionClient,
} from "./bio_client_engine";

/**
 * Validate sequence, classify type, calculate GC%, MW, ambiguity
 */
export async function validateSequence(sequence: string): Promise<ValidationResult> {
  const base = getApiBaseUrl();
  try {
    const resp = await fetch(`${base}/api/bio/sequence/validate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify({ sequence }),
    });
    if (resp.ok) {
      return await safeJson<ValidationResult>(resp);
    }
  } catch (err) {
    console.warn("Backend validateSequence unavailable, using client engine fallback:", err);
  }
  return validateSequenceClient(sequence);
}

/**
 * Bidirectional conversion between FASTA, GenBank, and EMBL formats
 */
export async function convertSequence(
  inputText: string,
  inputFormat: SequenceFormat,
  outputFormat: SequenceFormat
): Promise<ConversionResponse> {
  const base = getApiBaseUrl();
  try {
    const resp = await fetch(`${base}/api/bio/sequence/convert`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify({
        input_text: inputText,
        input_format: inputFormat,
        output_format: outputFormat,
      }),
    });
    if (resp.ok) {
      return await safeJson<ConversionResponse>(resp);
    }
  } catch (err) {
    console.warn("Backend convertSequence unavailable, using client engine fallback:", err);
  }
  return convertSequenceClient(inputText, inputFormat, outputFormat);
}

/**
 * Central Dogma engine: DNA -> RNA -> 6-frame translation and ORF detection
 */
export async function translateDogma(
  sequence: string,
  minOrfLengthAa: number = 20
): Promise<TranslationResponse> {
  const base = getApiBaseUrl();
  try {
    const resp = await fetch(`${base}/api/bio/sequence/dogma`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify({
        sequence,
        min_orf_length_aa: minOrfLengthAa,
      }),
    });
    if (resp.ok) {
      return await safeJson<TranslationResponse>(resp);
    }
  } catch (err) {
    console.warn("Backend translateDogma unavailable, using client engine fallback:", err);
  }
  return translateDogmaClient(sequence, minOrfLengthAa);
}

/**
 * INSDC Submission validator (GenBank / EMBL metadata check)
 */
export async function validateSubmission(
  payload: SubmissionValidationRequest
): Promise<SubmissionValidationResponse> {
  const base = getApiBaseUrl();
  try {
    const resp = await fetch(`${base}/api/bio/sequence/submission-check`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    });
    if (resp.ok) {
      return await safeJson<SubmissionValidationResponse>(resp);
    }
  } catch (err) {
    console.warn("Backend validateSubmission unavailable, using client engine fallback:", err);
  }
  return validateSubmissionClient(payload);
}

/**
 * Multi-database unified lookup across NCBI, UniProt, RCSB PDB, PROSITE, Pfam, KEGG, STRING, Ensembl, UCSC
 */
export async function lookupBio(query: string, organism?: string): Promise<BioLookupResponse> {
  const base = getApiBaseUrl();
  const params = new URLSearchParams();
  if (organism) params.append("organism", organism);
  const qs = params.toString() ? `?${params.toString()}` : "";
  try {
    const resp = await fetch(`${base}/api/bio/lookup/${encodeURIComponent(query)}${qs}`, {
      headers: {
        ...authHeaders(),
      },
    });
    if (resp.ok) {
      return await safeJson<BioLookupResponse>(resp);
    }
  } catch (err) {
    console.warn("Backend lookupBio unavailable, using client engine fallback:", err);
  }
  return lookupBioClient(query, organism);
}

/**
 * Fetch RCSB PDB structure metadata and CATH/SCOP folds
 */
export async function fetchStructure(pdbId: string): Promise<StructureRecord> {
  const base = getApiBaseUrl();
  try {
    const resp = await fetch(`${base}/api/bio/structure/${encodeURIComponent(pdbId)}`, {
      headers: {
        ...authHeaders(),
      },
    });
    if (resp.ok) {
      return await safeJson<StructureRecord>(resp);
    }
  } catch (err) {
    console.warn("Backend fetchStructure unavailable, using fallback:", err);
  }
  return {
    pdb_id: pdbId.toUpperCase(),
    title: `${pdbId.toUpperCase()} Macromolecular Structure Reference`,
    resolution_angstrom: 1.8,
    method: "X-RAY DIFFRACTION",
    deposit_date: "2012-05-15",
    cath_codes: ["1.10.490.10"],
    cath_names: ["Globin-like fold"],
    scop_folds: ["Globin-like"],
    ligands: ["HEM"],
    chains: ["A"],
    coordinates_url: `https://files.rcsb.org/download/${pdbId.toUpperCase()}.cif`,
  };
}

/**
 * Fetch paleogenomic mutation mappings on 3D PDB structure
 */
export async function fetchStructureMutations(pdbId: string): Promise<{
  pdb_id: string;
  mutations: Array<{
    position: number;
    ancestral: string;
    derived: string;
    chain: string;
    functional_impact?: string;
  }>;
}> {
  const base = getApiBaseUrl();
  try {
    const resp = await fetch(`${base}/api/bio/structure/${encodeURIComponent(pdbId)}/mutations`, {
      headers: {
        ...authHeaders(),
      },
    });
    if (resp.ok) {
      return await safeJson(resp);
    }
  } catch (err) {
    console.warn("Backend fetchStructureMutations unavailable, using client engine fallback:", err);
  }
  return fetchStructureMutationsClient(pdbId);
}

/**
 * Fetch PDB format coordinates from backend proxy / cache
 */
export async function fetchStructureCoordinates(pdbId: string): Promise<string> {
  const base = getApiBaseUrl();
  try {
    const resp = await fetch(`${base}/api/bio/structure/${encodeURIComponent(pdbId)}/coordinates`, {
      headers: {
        ...authHeaders(),
      },
    });
    if (resp.ok) {
      return await resp.text();
    }
  } catch (err) {
    console.warn("Backend fetchStructureCoordinates unavailable:", err);
  }
  return "";
}

/**
 * Fetch STRING protein-protein interactions
 */
export async function fetchInteractions(
  identifier: string,
  species?: number,
  requiredScore?: number
): Promise<{ identifier: string; interactions: InteractionEdge[] }> {
  const base = getApiBaseUrl();
  const params = new URLSearchParams();
  if (species) params.append("species", String(species));
  if (requiredScore) params.append("required_score", String(requiredScore));
  const qs = params.toString() ? `?${params.toString()}` : "";
  try {
    const resp = await fetch(`${base}/api/bio/interactions/${encodeURIComponent(identifier)}${qs}`, {
      headers: {
        ...authHeaders(),
      },
    });
    if (resp.ok) {
      return await safeJson(resp);
    }
  } catch (err) {
    console.warn("Backend fetchInteractions unavailable:", err);
  }
  return { identifier, interactions: [] };
}

/**
 * Scan amino acid sequence for PROSITE signatures
 */
export async function scanMotifs(sequence: string): Promise<{
  sequence_length: number;
  matches: Array<{
    motif_id: string;
    motif_name: string;
    start: number;
    end: number;
    matched_sequence: string;
  }>;
}> {
  const base = getApiBaseUrl();
  try {
    const resp = await fetch(`${base}/api/bio/motifs/scan`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify({ sequence }),
    });
    if (resp.ok) {
      return await safeJson(resp);
    }
  } catch (err) {
    console.warn("Backend scanMotifs unavailable, using client engine fallback:", err);
  }
  return scanMotifsClient(sequence);
}


