import React from "react";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Database,
  Dna,
  Microscope,
  Sparkles,
} from "lucide-react";

export type ViewKey =
  | "landing"
  | "atlas"
  | "workbench"
  | "biodb"
  | "studio"
  | "corpus"
  | "about"
  | "evaluation"
  | "diagnostics";

interface AboutPlatformViewProps {
  onNavigate: (view: ViewKey) => void;
  onSelectTaxonWorkflow?: (taxonId: string, module: "atlas" | "workbench" | "studio") => void;
}

export function AboutPlatformView({
  onNavigate,
  onSelectTaxonWorkflow,
}: AboutPlatformViewProps) {
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
      <div className="mx-auto max-w-5xl space-y-10">
        {/* HEADER */}
        <section className="space-y-3 border-b border-white/[0.08] pb-6">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[#d5a65b]">
            <Sparkles size={12} />
            <span>Platform Specifications &amp; Architecture</span>
          </div>
          <h1 className="font-display text-2xl font-semibold text-[#eee9de] sm:text-3xl">
            About the PaleoDB Platform
          </h1>
          <p className="max-w-3xl text-sm leading-relaxed text-slate-400">
            PaleoDB integrates paleogenomics, molecular biology, and deep-time evolutionary anthropology
            into a unified bioinformatics platform. Below is a complete overview of the platform's architectural
            modules, computational capabilities, and guided research workflows.
          </p>
        </section>

        {/* CORE PLATFORM CAPABILITIES */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#d5a65b]">Modules</div>
              <h2 className="font-display text-lg text-[#eee9de]">Four Core Pillars</h2>
            </div>
            <span className="font-mono text-[10px] text-slate-500">Integrated Bio-Suite</span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* PILLAR 1: ATLAS */}
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
                <h3 className="font-display text-base text-[#eee9de]">Prehistoric Genetic Archives</h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Comprehensive dossiers for 18 prehistoric taxa covering taxonomy, geological epochs,
                  key evolutionary traits, target loci, extant relatives, and authentic lead photography.
                </p>
                <ul className="space-y-1.5 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>Pairwise Synteny:</strong> Divergence % &amp; amino acid substitution mapping</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>3D Molecular Viewer:</strong> Real RCSB PDB crystal structures with mutation residue badges</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>Paleobiology Database:</strong> Stratigraphic occurrences &amp; PBDB Navigator links</span>
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

            {/* PILLAR 2: SEQUENCE WORKBENCH */}
            <div className="flex flex-col justify-between border border-white/[0.08] bg-[#0f1516] p-5 transition hover:border-[#70c4b5]/40">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#70c4b5]">
                    <Dna size={16} />
                    <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-semibold">02 / Sequence Workbench</span>
                  </div>
                  <span className="border border-[#70c4b5]/30 bg-[#70c4b5]/10 px-2 py-0.5 font-mono text-[9px] text-[#70c4b5]">
                    Bio-Algorithms
                  </span>
                </div>
                <h3 className="font-display text-base text-[#eee9de]">Sequence Manipulation &amp; Alignment</h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Specialized toolkit for analyzing ancient DNA and protein fragments, computing nucleotide metrics,
                  and performing pairwise sequence alignment against living counterparts.
                </p>
                <ul className="space-y-1.5 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>IUPAC Validation:</strong> Strict nucleic/amino acid alphabet checks &amp; deamination warnings</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>Composition Metrics:</strong> GC content, CpG island detection, and 6-frame ORF scanning</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>Pairwise Alignment:</strong> Needleman-Wunsch / Smith-Waterman with Grantham scoring</span>
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

            {/* PILLAR 3: BIODB MULTI-EXPLORER */}
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
                <h3 className="font-display text-base text-[#eee9de]">Federated Multi-Database Queries</h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Executes parallel queries across the major biological and paleontological repositories,
                  harmonizing disparate metadata into a single interactive view.
                </p>
                <ul className="space-y-1.5 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>NCBI &amp; UniProt:</strong> Fetch nucleotide accessions, annotations, and curated protein entries</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>RCSB &amp; KEGG:</strong> 3D coordinate metadata and biochemical pathway maps</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
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

            {/* PILLAR 4: LITERATURE COPILOT */}
            <div className="flex flex-col justify-between border border-white/[0.08] bg-[#0f1516] p-5 transition hover:border-[#d5a65b]/40">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#f0c778]">
                    <Microscope size={16} />
                    <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-semibold">04 / Literature Copilot (RAG)</span>
                  </div>
                  <span className="border border-[#d5a65b]/30 bg-[#d5a65b]/10 px-2 py-0.5 font-mono text-[9px] text-[#f0c778]">
                    Literature Grounding
                  </span>
                </div>
                <h3 className="font-display text-base text-[#eee9de]">Domain-Grounded Literature Search</h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Retrieval-Augmented Generation tailored for paleogenomic papers. Combines dense
                  vector embeddings and sparse BM25 with taxonomic synonym expansion to prevent hallucinations.
                </p>
                <ul className="space-y-1.5 text-xs text-slate-400">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>Hybrid Search (RRF k=60):</strong> Fuses semantic concepts with exact gene loci</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
                    <span><strong>Taxonomic Expansion:</strong> Resolves common names across GBIF and PBDB taxonomy graphs</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-[#70c4b5] shrink-0" />
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

        {/* GUIDED WORKFLOWS */}
        <section className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#d5a65b]">Workflows</div>
              <h2 className="font-display text-lg text-[#eee9de]">Sample Research Trajectories</h2>
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
      </div>
    </div>
  );
}
