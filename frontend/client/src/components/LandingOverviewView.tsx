import React from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  Database,
  Dna,
  ExternalLink,
  FileText,
  Gauge,
  GitCompare,
  Layers,
  Microscope,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export type ViewKey =
  | "overview"
  | "atlas"
  | "workbench"
  | "biodb"
  | "studio"
  | "corpus"
  | "evaluation"
  | "diagnostics";

interface LandingOverviewViewProps {
  onNavigate: (view: ViewKey) => void;
  onSelectTaxonWorkflow?: (taxonId: string, module: "atlas" | "workbench" | "studio") => void;
}

export function LandingOverviewView({
  onNavigate,
  onSelectTaxonWorkflow,
}: LandingOverviewViewProps) {
  const guidedWorkflows = [
    {
      title: "Mammoth Cold-Adaptation Phenotype",
      taxon: "Mammuthus primigenius",
      taxId: "PRAG-TAX-001",
      steps: "Atlas (HBB locus) → Pairwise Alignment (vs Asian Elephant) → 3D Tetramer (3VRF) → Literature Copilot",
      citation: "Campbell et al. (2010) Nature Genetics",
      badge: "Proboscidea",
      color: "#d5a65b",
    },
    {
      title: "Dire Wolf Deep Evolutionary Isolation",
      taxon: "Aenocyon dirus",
      taxId: "PRAG-TAX-004",
      steps: "Atlas (CYTB locus) → Canid Synteny Divergence → BioDB (PBDB 86 Occurrences) → RAG Synthesis",
      citation: "Perri et al. (2021) Nature",
      badge: "Carnivora",
      color: "#70c4b5",
    },
    {
      title: "Neanderthal Pigmentation & MC1R Allele",
      taxon: "Homo neanderthalensis",
      taxId: "PRAG-TAX-002",
      steps: "Atlas (MC1R locus) → R307G Substitution → 3D Receptor (7F53) → Paleogenomic Verification",
      citation: "Lalueza-Fox et al. (2007) Science",
      badge: "Hominidae",
      color: "#f0c778",
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto px-5 py-8 md:px-12 md:py-10">
      <div className="mx-auto max-w-6xl space-y-12">
        {/* HERO SECTION */}
        <section className="relative border border-white/[0.08] bg-[#0e1315] p-6 md:p-10">
          <div className="absolute right-0 top-0 h-40 w-40 bg-[#d5a65b]/[0.03] blur-3xl pointer-events-none" />
          <div className="absolute left-1/3 bottom-0 h-40 w-40 bg-[#70c4b5]/[0.03] blur-3xl pointer-events-none" />

          <div className="relative space-y-6">
            <div className="flex flex-wrap items-center gap-3 font-mono text-[10px] uppercase tracking-[0.2em]">
              <span className="inline-flex items-center gap-1.5 border border-[#d5a65b]/40 bg-[#d5a65b]/10 px-2.5 py-1 text-[#f0c778]">
                <Sparkles size={11} /> PaleoDB Platform
              </span>
              <span className="text-slate-500">Paleogenomics · Deep-Time Synteny · Grounded RAG</span>
            </div>

            <div className="space-y-3">
              <h1 className="font-display text-3xl font-semibold tracking-tight text-[#eee9de] sm:text-4xl md:text-5xl">
                Prehistoric Biomolecular &amp; Evolutionary Intelligence
              </h1>
              <p className="max-w-3xl text-sm leading-relaxed text-slate-400 sm:text-base">
                A unified bioinformatics workbench built specifically for ancient DNA (aDNA) and extinct organisms.
                Inspect 18 codified prehistoric taxa, analyze extant pairwise synteny, visualize 3D structural
                adaptation mutations, query 6 federated biological databases, and synthesize paleogenomic literature
                with closed-domain Retrieval-Augmented Generation.
              </p>
            </div>

            {/* QUICK ACTIONS */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={() => onNavigate("atlas")}
                className="flex items-center gap-2 border border-[#d5a65b] bg-[#d5a65b]/15 px-4 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-[#f0c778] transition hover:bg-[#d5a65b]/25"
              >
                <BookOpen size={14} />
                <span>Explore Taxa Atlas (18 Taxa)</span>
                <ArrowRight size={13} />
              </button>

              <button
                onClick={() => onNavigate("workbench")}
                className="flex items-center gap-2 border border-white/15 bg-white/[0.03] px-4 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#70c4b5]/50 hover:bg-[#70c4b5]/10 hover:text-[#8cd1c7]"
              >
                <Dna size={14} />
                <span>Sequence Workbench</span>
              </button>

              <button
                onClick={() => onNavigate("biodb")}
                className="flex items-center gap-2 border border-white/15 bg-white/[0.03] px-4 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#70c4b5]/50 hover:bg-[#70c4b5]/10 hover:text-[#8cd1c7]"
              >
                <Database size={14} />
                <span>BioDB Multi-Explorer</span>
              </button>

              <button
                onClick={() => onNavigate("studio")}
                className="flex items-center gap-2 border border-white/15 bg-white/[0.03] px-4 py-2.5 font-mono text-xs uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#d5a65b]/50 hover:bg-[#d5a65b]/10 hover:text-[#f0c778]"
              >
                <Microscope size={14} />
                <span>Literature Copilot (RAG)</span>
              </button>
            </div>
          </div>

          {/* TELEMETRY METRICS STRIP */}
          <div className="mt-8 grid grid-cols-2 gap-3 border-t border-white/[0.08] pt-6 sm:grid-cols-4">
            <div className="border border-white/[0.06] bg-black/20 p-3">
              <div className="font-mono text-lg font-bold text-[#f0c778]">18 Taxa</div>
              <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-400">Codified Prehistoric Records</div>
              <p className="mt-1 text-[11px] text-slate-500">Pleistocene megafauna, hominins, avian ratites &amp; ancient pathogens</p>
            </div>

            <div className="border border-white/[0.06] bg-black/20 p-3">
              <div className="font-mono text-lg font-bold text-[#70c4b5]">6 Databases</div>
              <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-400">Federated Bio Integrations</div>
              <p className="mt-1 text-[11px] text-slate-500">NCBI Entrez, UniProt, RCSB PDB, KEGG, Ensembl &amp; PBDB</p>
            </div>

            <div className="border border-white/[0.06] bg-black/20 p-3">
              <div className="font-mono text-lg font-bold text-[#d5a65b]">Hybrid RRF</div>
              <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-400">Dense + Sparse Vector Search</div>
              <p className="mt-1 text-[11px] text-slate-500">Reciprocal rank fusion (k=60) with GBIF/PBDB taxonomic expansion</p>
            </div>

            <div className="border border-white/[0.06] bg-black/20 p-3">
              <div className="font-mono text-lg font-bold text-[#8cd1c7]">84 Tests</div>
              <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-400">100% Suite Passing</div>
              <p className="mt-1 text-[11px] text-slate-500">Comprehensive unit, integration, RAG retrieval &amp; regression tests</p>
            </div>
          </div>
        </section>

        {/* CORE PLATFORM CAPABILITIES */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#d5a65b]">Architecture &amp; Features</div>
              <h2 className="font-display text-xl text-[#eee9de]">Four Core Pillars of the Platform</h2>
            </div>
            <span className="font-mono text-[10px] text-slate-500">Full Stack Paleogenomics</span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* CARD 1: ATLAS */}
            <div className="flex flex-col justify-between border border-white/[0.08] bg-[#0f1516] p-5 transition hover:border-[#d5a65b]/40">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#f0c778]">
                    <BookOpen size={16} />
                    <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-semibold">01 / Taxa Atlas &amp; Registry</span>
                  </div>
                  <span className="border border-[#d5a65b]/30 bg-[#d5a65b]/10 px-2 py-0.5 font-mono text-[9px] text-[#f0c778]">
                    18 Taxa
                  </span>
                </div>
                <h3 className="font-display text-base text-[#eee9de]">Codified Prehistoric Genetic Archives</h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Detailed dossiers for 18 prehistoric organisms covering biological taxonomy, geological epochs,
                  key evolutionary traits, verified target loci, extant relatives, and authentic lead photography.
                </p>
                <ul className="space-y-1 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>Extant Pairwise Synteny:</strong> Divergence % &amp; amino acid substitution mapping</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>3D Molecular Viewer:</strong> Real RCSB PDB crystal structures with mutation residue badges</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>Paleobiology Database:</strong> Real stratigraphic occurrences &amp; PBDB Navigator links</span>
                  </li>
                </ul>
              </div>
              <button
                onClick={() => onNavigate("atlas")}
                className="mt-5 flex items-center justify-between border border-white/10 bg-black/20 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#d5a65b]/60 hover:text-[#f0c778]"
              >
                <span>Launch Taxa Atlas</span>
                <ArrowRight size={12} />
              </button>
            </div>

            {/* CARD 2: SEQUENCE WORKBENCH */}
            <div className="flex flex-col justify-between border border-white/[0.08] bg-[#0f1516] p-5 transition hover:border-[#70c4b5]/40">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#70c4b5]">
                    <Dna size={16} />
                    <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-semibold">02 / Sequence Workbench</span>
                  </div>
                  <span className="border border-[#70c4b5]/30 bg-[#70c4b5]/10 px-2 py-0.5 font-mono text-[9px] text-[#70c4b5]">
                    Algorithmics
                  </span>
                </div>
                <h3 className="font-display text-base text-[#eee9de]">Bioinformatics Sequence Manipulation</h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Specialized toolkit for analyzing ancient DNA and protein fragments, computing nucleotide metrics,
                  and performing pairwise sequence alignment against living counterparts.
                </p>
                <ul className="space-y-1 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>IUPAC Validation:</strong> Strict nucleic/amino acid alphabet checks &amp; deamination warning</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>Composition Metrics:</strong> GC content, CpG island detection, and 6-frame ORF scanning</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>Pairwise Alignment:</strong> Global Needleman-Wunsch / Local Smith-Waterman with Grantham scoring</span>
                  </li>
                </ul>
              </div>
              <button
                onClick={() => onNavigate("workbench")}
                className="mt-5 flex items-center justify-between border border-white/10 bg-black/20 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#70c4b5]/60 hover:text-[#70c4b5]"
              >
                <span>Launch Sequence Workbench</span>
                <ArrowRight size={12} />
              </button>
            </div>

            {/* CARD 3: BIODB MULTI-EXPLORER */}
            <div className="flex flex-col justify-between border border-white/[0.08] bg-[#0f1516] p-5 transition hover:border-[#70c4b5]/40">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#70c4b5]">
                    <Database size={16} />
                    <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-semibold">03 / BioDB Multi-Explorer</span>
                  </div>
                  <span className="border border-[#70c4b5]/30 bg-[#70c4b5]/10 px-2 py-0.5 font-mono text-[9px] text-[#70c4b5]">
                    6 REST Feeds
                  </span>
                </div>
                <h3 className="font-display text-base text-[#eee9de]">Federated Cross-Database Querying</h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Executes parallel queries across the major biological and paleontological repositories,
                  harmonizing disparate metadata into a single interactive view.
                </p>
                <ul className="space-y-1 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>NCBI &amp; UniProt:</strong> Fetch nucleotide accessions, annotations, and curated protein entries</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>RCSB &amp; KEGG:</strong> 3D coordinate metadata and biochemical pathway maps</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>Ensembl &amp; PBDB:</strong> Genomic coordinates, chromosomal loci, and fossil collections</span>
                  </li>
                </ul>
              </div>
              <button
                onClick={() => onNavigate("biodb")}
                className="mt-5 flex items-center justify-between border border-white/10 bg-black/20 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#70c4b5]/60 hover:text-[#70c4b5]"
              >
                <span>Launch BioDB Multi-Explorer</span>
                <ArrowRight size={12} />
              </button>
            </div>

            {/* CARD 4: LITERATURE COPILOT RAG */}
            <div className="flex flex-col justify-between border border-white/[0.08] bg-[#0f1516] p-5 transition hover:border-[#d5a65b]/40">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#f0c778]">
                    <Microscope size={16} />
                    <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-semibold">04 / Literature Copilot (RAG)</span>
                  </div>
                  <span className="border border-[#d5a65b]/30 bg-[#d5a65b]/10 px-2 py-0.5 font-mono text-[9px] text-[#f0c778]">
                    Grounded RAG
                  </span>
                </div>
                <h3 className="font-display text-base text-[#eee9de]">Domain-Grounded Paleogenomic Synthesis</h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Retrieval-Augmented Generation tailored specifically for paleogenomic papers. Combines dense
                  vector embeddings and sparse BM25 with taxonomic synonym expansion to prevent hallucinations.
                </p>
                <ul className="space-y-1 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>Hybrid Search (RRF k=60):</strong> Fuses semantic concepts with exact gene loci</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>Taxonomic Expansion:</strong> Resolves common names across GBIF and PBDB taxonomy graphs</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5]" />
                    <span><strong>Evidence Attribution:</strong> Every claim verified with chunk-level citations and DOI links</span>
                  </li>
                </ul>
              </div>
              <button
                onClick={() => onNavigate("studio")}
                className="mt-5 flex items-center justify-between border border-white/10 bg-black/20 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#d5a65b]/60 hover:text-[#f0c778]"
              >
                <span>Launch Literature Copilot</span>
                <ArrowRight size={12} />
              </button>
            </div>
          </div>
        </section>

        {/* WHY RAG IN PALEOGENOMICS (CRITICAL JUSTIFICATION) */}
        <section className="border border-[#d5a65b]/30 bg-[#0e1416] p-6 md:p-8">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-4">
              <div>
                <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#d5a65b]">
                  Architectural Rationale
                </div>
                <h2 className="font-display text-xl text-[#eee9de] sm:text-2xl">
                  Why is RAG Essential to this Project?
                </h2>
              </div>
              <span className="border border-[#70c4b5]/40 bg-[#70c4b5]/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-[#8cd1c7]">
                Scientific Grounding
              </span>
            </div>

            <p className="text-sm leading-relaxed text-slate-300">
              In standard bioinformatics platforms, databases and sequence visualizers show you <em>what</em> a sequence is
              and <em>where</em> its mutations reside. But in deep-time paleobiology, <strong>RAG is the critical bridge that explains <em>why</em></strong>.
              Without RAG, a bioinformatician would see isolated letters without understanding the physiological adaptations,
              taphonomic degradation artifacts, or geological context.
            </p>

            <div className="grid gap-4 sm:grid-cols-2 pt-2">
              <div className="border border-white/[0.06] bg-black/25 p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#f0c778]">
                  <Layers size={14} />
                  <span>1. 95% of aDNA Knowledge is Unstructured</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-400">
                  Unlike modern model organisms with clean structured database entries, ancient DNA insights
                  (radiocarbon calibration, deamination patterns, skeletal morphology, ecological niche) exist
                  exclusively as narrative prose and tables inside scientific literature. RAG unlocks this text.
                </p>
              </div>

              <div className="border border-white/[0.06] bg-black/25 p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#70c4b5]">
                  <GitCompare size={14} />
                  <span>2. Sequence → Structure → Evolutionary 'Why'</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-400">
                  The Sequence Workbench computes the <code>T12A / A86S / E101Q</code> substitutions; the 3D viewer renders
                  the tetramer. Only the RAG copilot retrieves Campbell et al. (2010) to explain that these three mutations
                  specifically abolish the temperature-dependence of oxygen affinity for arctic peripheral limb survival.
                </p>
              </div>

              <div className="border border-white/[0.06] bg-black/25 p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#8cd1c7]">
                  <ShieldCheck size={14} />
                  <span>3. Eliminating Hallucinations in Deep Time</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-400">
                  General-purpose LLMs conflate extinct organisms with extant counterparts, invent fictitious radiocarbon dates,
                  or misattribute gene functions. PaleoDB's closed-domain RAG guarantees zero-hallucination answers backed by
                  verifiable chunk-level citations with active PMC/DOI links.
                </p>
              </div>

              <div className="border border-white/[0.06] bg-black/25 p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#d5a65b]">
                  <Search size={14} />
                  <span>4. Taxonomic-Aware Query Disambiguation</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-400">
                  Paleobiology suffers from constant taxonomic reclassifications (e.g. <em>Canis dirus</em> vs <em>Aenocyon dirus</em>).
                  Our pipeline integrates a GBIF/PBDB synonym graph into the retrieval step, ensuring literature from both historical
                  and modern nomenclature is retrieved accurately.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* GUIDED WORKFLOWS */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#d5a65b]">Interactive Trajectories</div>
              <h2 className="font-display text-xl text-[#eee9de]">Sample Guided Research Workflows</h2>
            </div>
            <span className="font-mono text-[10px] text-slate-500">Cross-Module Integration</span>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {guidedWorkflows.map((flow) => (
              <div
                key={flow.taxId}
                className="flex flex-col justify-between border border-white/[0.08] bg-[#0f1516] p-4 transition hover:border-[#d5a65b]/50"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span
                      className="border px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em]"
                      style={{ borderColor: `${flow.color}40`, color: flow.color, backgroundColor: `${flow.color}10` }}
                    >
                      {flow.badge}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500">{flow.taxId}</span>
                  </div>
                  <h4 className="font-display text-sm font-semibold text-[#eee9de]">{flow.title}</h4>
                  <div className="font-mono text-[11px] italic text-slate-400">{flow.taxon}</div>
                  <p className="text-[11px] leading-relaxed text-slate-500">{flow.steps}</p>
                  <div className="font-mono text-[10px] text-[#8cd1c7]">Key Paper: {flow.citation}</div>
                </div>

                <button
                  onClick={() => {
                    if (onSelectTaxonWorkflow) {
                      onSelectTaxonWorkflow(flow.taxId, "atlas");
                    } else {
                      onNavigate("atlas");
                    }
                  }}
                  className="mt-4 flex items-center justify-between border border-white/10 bg-black/20 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#d5a65b] hover:text-[#f0c778]"
                >
                  <span>Launch Journey</span>
                  <ArrowRight size={12} />
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* FOOTER METADATA */}
        <footer className="border-t border-white/[0.08] pt-6 pb-2 text-center">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
            PaleoDB · Prehistoric Biomolecular &amp; Evolutionary Database · Open Science &amp; Paleogenomics
          </p>
        </footer>
      </div>
    </div>
  );
}
