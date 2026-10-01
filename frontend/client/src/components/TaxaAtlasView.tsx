import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Box,
  Check,
  ChevronRight,
  Clock,
  Compass,
  Copy,
  Database,
  Dna,
  ExternalLink,
  Filter,
  Flame,
  GitBranch,
  Layers,
  Microscope,
  Network,
  RotateCw,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  AtlasListResponse,
  fetchAtlas,
  TaxonRegistryEntry,
} from "../lib/api";
import { MolecularViewer } from "./MolecularViewer";

interface TaxaAtlasViewProps {
  onExploreInBioDB?: (query: string, organism: string) => void;
  onLoadInWorkbench?: (sequence: string, locus: string, organism: string) => void;
  onAskInStudio?: (prompt: string, taxon: string) => void;
}

export const TaxaAtlasView: React.FC<TaxaAtlasViewProps> = ({
  onExploreInBioDB,
  onLoadInWorkbench,
  onAskInStudio,
}) => {
  const [taxa, setTaxa] = useState<TaxonRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedClade, setSelectedClade] = useState<string>("All");
  const [selectedEpoch, setSelectedEpoch] = useState<string>("All");
  const [activeTaxon, setActiveTaxon] = useState<TaxonRegistryEntry | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "comparative" | "structure" | "genomics">("overview");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Load atlas from backend or client fallback
  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      try {
        const res = await fetchAtlas();
        if (mounted) {
          const list = res.taxa || res.catalog || [];
          setTaxa(list);
          if (list.length > 0 && !activeTaxon) {
            setActiveTaxon(list[0]);
          }
        }
      } catch (err: any) {
        console.error("Failed to load atlas:", err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  // Distinct Clades
  const clades = useMemo(() => {
    const set = new Set<string>();
    taxa.forEach((t) => {
      if (t.clade) set.add(t.clade);
    });
    return ["All", ...Array.from(set).sort()];
  }, [taxa]);

  // Distinct Epoch groups
  const epochs = useMemo(() => {
    return ["All", "Late Pleistocene", "Holocene", "Historic / Anthropocene"];
  }, []);

  // Filtered Taxa
  const filteredTaxa = useMemo(() => {
    return taxa.filter((t) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesQuery =
        !q ||
        t.tax_id.toLowerCase().includes(q) ||
        t.common_name.toLowerCase().includes(q) ||
        t.scientific_name.toLowerCase().includes(q) ||
        t.clade.toLowerCase().includes(q) ||
        t.key_trait.toLowerCase().includes(q) ||
        t.target_locus.gene_symbol.toLowerCase().includes(q) ||
        t.target_locus.protein_name.toLowerCase().includes(q) ||
        t.extant_counterpart.scientific_name.toLowerCase().includes(q) ||
        t.extant_counterpart.common_name.toLowerCase().includes(q);

      const matchesClade =
        selectedClade === "All" ||
        t.clade.toLowerCase() === selectedClade.toLowerCase();

      let matchesEpoch = true;
      if (selectedEpoch === "Late Pleistocene") {
        matchesEpoch = t.epoch.toLowerCase().includes("pleistocene");
      } else if (selectedEpoch === "Holocene") {
        matchesEpoch =
          t.epoch.toLowerCase().includes("holocene") ||
          t.extinction_date.toLowerCase().includes("bp");
      } else if (selectedEpoch === "Historic / Anthropocene") {
        matchesEpoch =
          t.extinction_date.includes("1") ||
          t.extinction_date.includes("20th") ||
          t.epoch.toLowerCase().includes("historic");
      }

      return matchesQuery && matchesClade && matchesEpoch;
    });
  }, [taxa, searchQuery, selectedClade, selectedEpoch]);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success("Sequence copied to clipboard");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Compute sequence pairwise comparison stats
  const comparisonStats = useMemo(() => {
    if (!activeTaxon) return null;
    const anc = activeTaxon.target_locus.extinct_sequence_aa || "";
    const ext = activeTaxon.extant_counterpart.extant_sequence_aa || "";
    const minLen = Math.min(anc.length, ext.length);
    let matches = 0;
    const diffs: Array<{ pos: number; anc: string; ext: string }> = [];

    for (let i = 0; i < minLen; i++) {
      if (anc[i] === ext[i]) {
        matches++;
      } else {
        diffs.push({ pos: i + 1, anc: anc[i], ext: ext[i] });
      }
    }

    const identityPct = minLen > 0 ? ((matches / minLen) * 100).toFixed(1) : "0";
    const divergencePct = minLen > 0 ? (100 - parseFloat(identityPct)).toFixed(1) : "0";

    return {
      ancLen: anc.length,
      extLen: ext.length,
      matches,
      divergencePct,
      identityPct,
      diffs,
    };
  }, [activeTaxon]);

  return (
    <div className="min-h-0 flex-1 overflow-auto p-4 md:p-8">
      {/* Header */}
      <div className="mb-6 flex flex-col justify-between gap-4 border-b border-white/[0.08] pb-6 md:flex-row md:items-end">
        <div>
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[#d5a65b]">
            <BookOpen size={13} />
            <span>Phylogenetic Registry & Evolutionary Atlas</span>
            <span className="rounded bg-[#d5a65b]/20 px-1.5 py-0.5 text-[#f0c778]">
              {taxa.length} Codified Taxa
            </span>
          </div>
          <h1 className="mt-2 font-display text-2xl text-[#eee9de] md:text-3xl">
            Prehistoric Taxa Atlas
          </h1>
          <p className="mt-1.5 max-w-3xl text-xs leading-relaxed text-slate-400">
            A comprehensive genomic and proteomic directory of Pleistocene and Holocene taxa, ancient pathogens, and
            island endemics. Explores preserved ancient DNA loci, extant sister-taxon alignments, 3D structural homologs, and
            paleo-adaptive mutations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 border border-white/10 bg-[#0d1213] px-3 py-1.5 font-mono text-[11px] text-slate-300">
            <span className="h-2 w-2 rounded-full bg-[#4f9f96]" />
            <span>18 Taxa Indexed</span>
          </div>
          <div className="flex items-center gap-2 border border-white/10 bg-[#0d1213] px-3 py-1.5 font-mono text-[11px] text-slate-300">
            <span className="h-2 w-2 rounded-full bg-[#d5a65b]" />
            <span>100% Extant Comparative Alignments</span>
          </div>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="mb-6 space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search
              size={14}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by taxon accession (PRAG-TAX-001), scientific name (Smilodon), gene (HBB), or adaptive trait..."
              className="w-full border border-white/10 bg-[#0d1213] py-2.5 pl-10 pr-4 font-mono text-xs text-[#eee9de] placeholder-slate-600 transition focus:border-[#d5a65b]/60 focus:outline-none"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
              >
                <X size={13} />
              </button>
            )}
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">
            <Filter size={11} /> Clade:
          </span>
          {clades.map((clade) => (
            <button
              key={clade}
              onClick={() => setSelectedClade(clade)}
              className={`px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider transition ${
                selectedClade === clade
                  ? "border border-[#d5a65b]/60 bg-[#d5a65b]/20 font-semibold text-[#f0c778]"
                  : "border border-white/[0.08] bg-[#0d1213] text-slate-400 hover:border-white/20 hover:text-slate-200"
              }`}
            >
              {clade}
            </button>
          ))}
        </div>
      </div>

      {/* Main Two-Column Layout: Catalog Grid + Detail Inspector */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {/* Left: Specimen Grid (7 cols) */}
        <div className="space-y-3 xl:col-span-7">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-2 font-mono text-[10px] uppercase tracking-wider text-slate-500">
            <span>
              Showing {filteredTaxa.length} of {taxa.length} Taxa
            </span>
            <span>Click any specimen card to inspect details</span>
          </div>

          {filteredTaxa.length === 0 ? (
            <div className="border border-dashed border-white/10 p-12 text-center text-sm text-slate-500">
              No prehistoric taxa matched the selected query or filters.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {filteredTaxa.map((item) => {
                const isSelected = activeTaxon?.tax_id === item.tax_id;
                return (
                  <div
                    key={item.tax_id}
                    onClick={() => setActiveTaxon(item)}
                    className={`group relative flex cursor-pointer flex-col justify-between border p-4 transition ${
                      isSelected
                        ? "border-[#d5a65b] bg-[#151c1d] shadow-lg shadow-black/40"
                        : "border-white/[0.08] bg-[#0d1213] hover:border-white/20 hover:bg-[#111718]"
                    }`}
                  >
                    <div>
                      {/* Top Badges */}
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[10px] font-semibold text-[#d5a65b]">
                          {item.tax_id}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="border border-white/10 bg-black/40 px-1.5 py-0.5 font-mono text-[9px] text-slate-400">
                            {item.clade}
                          </span>
                        </div>
                      </div>

                      {/* Taxon Names */}
                      <div className="mt-2.5">
                        <div className="font-display text-base font-semibold text-[#eee9de] group-hover:text-white">
                          {item.common_name}
                        </div>
                        <div className="font-serif italic text-xs text-[#8cd1c7]">
                          {item.scientific_name}
                        </div>
                      </div>

                      {/* Key Adaptive Trait */}
                      <div className="mt-3 flex items-start gap-1.5 rounded bg-white/[0.03] p-2 text-[11px] leading-snug text-slate-300">
                        <Sparkles size={12} className="mt-0.5 shrink-0 text-[#d5a65b]" />
                        <div>
                          <span className="font-semibold text-[#f0c778]">{item.key_trait}: </span>
                          <span className="line-clamp-2 text-slate-400">{item.description}</span>
                        </div>
                      </div>

                      {/* Target Locus & Extant Comparison */}
                      <div className="mt-3 grid grid-cols-2 gap-2 border-t border-white/[0.06] pt-3 font-mono text-[10px]">
                        <div>
                          <div className="text-slate-500 uppercase">Target Gene</div>
                          <div className="font-semibold text-[#eee9de]">
                            {item.target_locus.gene_symbol} ({item.target_locus.extinct_nucleotide_acc})
                          </div>
                        </div>
                        <div>
                          <div className="text-slate-500 uppercase">Extant Sister</div>
                          <div className="truncate text-slate-300 font-serif italic">
                            {item.extant_counterpart.scientific_name}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Bottom Action Footer */}
                    <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-3 text-[11px]">
                      <span className="font-mono text-[9px] text-slate-500">
                        {item.extinction_date}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveTaxon(item);
                        }}
                        className="flex items-center gap-1 font-mono text-[10px] uppercase text-[#d5a65b] transition hover:text-[#f0c778]"
                      >
                        Inspect Specimen <ChevronRight size={11} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Detailed Specimen Inspector (5 cols) */}
        <div className="xl:col-span-5">
          {activeTaxon ? (
            <div className="sticky top-6 border border-white/10 bg-[#0f1516] p-5 shadow-2xl">
              {/* Specimen Header */}
              <div className="flex items-start justify-between border-b border-white/[0.08] pb-4">
                <div>
                  <div className="flex items-center gap-2 font-mono text-[10px] text-[#d5a65b]">
                    <span className="font-bold">{activeTaxon.tax_id}</span>
                    <span>·</span>
                    <span>{activeTaxon.clade}</span>
                  </div>
                  <h2 className="mt-1 font-display text-xl text-[#eee9de]">
                    {activeTaxon.common_name}
                  </h2>
                  <div className="font-serif italic text-sm text-[#8cd1c7]">
                    {activeTaxon.scientific_name}
                  </div>
                </div>

                <div className="text-right">
                  <span className="inline-block border border-white/10 bg-black/40 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                    {activeTaxon.extinction_date}
                  </span>
                </div>
              </div>

              {/* Inspector Nav Tabs */}
              <div className="mt-4 flex border-b border-white/[0.08] font-mono text-[11px]">
                <button
                  onClick={() => setActiveTab("overview")}
                  className={`flex items-center gap-1.5 border-b-2 px-3 py-2 transition ${
                    activeTab === "overview"
                      ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <Activity size={12} />
                  Overview
                </button>
                <button
                  onClick={() => setActiveTab("comparative")}
                  className={`flex items-center gap-1.5 border-b-2 px-3 py-2 transition ${
                    activeTab === "comparative"
                      ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <GitBranch size={12} />
                  Extant Alignment
                </button>
                <button
                  onClick={() => setActiveTab("structure")}
                  className={`flex items-center gap-1.5 border-b-2 px-3 py-2 transition ${
                    activeTab === "structure"
                      ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <Box size={12} />
                  3D Structure
                </button>
                <button
                  onClick={() => setActiveTab("genomics")}
                  className={`flex items-center gap-1.5 border-b-2 px-3 py-2 transition ${
                    activeTab === "genomics"
                      ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <Compass size={12} />
                  Genomics & KEGG
                </button>
              </div>

              {/* Tab 1: Overview */}
              {activeTab === "overview" && (
                <div className="mt-4 space-y-4 text-xs">
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      Adaptive Trait & Evolutionary Significance
                    </div>
                    <div className="mt-1 text-sm font-semibold text-[#eee9de]">
                      {activeTaxon.key_trait}
                    </div>
                    <p className="mt-1.5 leading-relaxed text-slate-300">
                      {activeTaxon.description}
                    </p>
                  </div>

                  <div className="border-t border-white/[0.06] pt-3">
                    <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      Target Ancient Locus
                    </div>
                    <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                      <div className="rounded border border-white/[0.06] bg-black/30 p-2">
                        <div className="text-[9px] uppercase text-slate-500">Gene Symbol</div>
                        <div className="font-bold text-[#d5a65b]">
                          {activeTaxon.target_locus.gene_symbol}
                        </div>
                      </div>
                      <div className="rounded border border-white/[0.06] bg-black/30 p-2">
                        <div className="text-[9px] uppercase text-slate-500">NCBI Accession</div>
                        <div className="font-bold text-slate-200">
                          {activeTaxon.target_locus.extinct_nucleotide_acc}
                        </div>
                      </div>
                      <div className="rounded border border-white/[0.06] bg-black/30 p-2">
                        <div className="text-[9px] uppercase text-slate-500">UniProtKB</div>
                        <div className="font-bold text-slate-200">
                          {activeTaxon.target_locus.extinct_uniprot_acc}
                        </div>
                      </div>
                      <div className="rounded border border-white/[0.06] bg-black/30 p-2">
                        <div className="text-[9px] uppercase text-slate-500">Protein Product</div>
                        <div className="truncate font-bold text-slate-200" title={activeTaxon.target_locus.protein_name}>
                          {activeTaxon.target_locus.protein_name}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Quick Action Buttons */}
                  <div className="border-t border-white/[0.06] pt-4">
                    <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      Integrated Workflow Actions
                    </div>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <button
                        onClick={() => {
                          if (onExploreInBioDB) {
                            onExploreInBioDB(
                              activeTaxon.target_locus.gene_symbol,
                              activeTaxon.scientific_name
                            );
                          } else {
                            toast.info(`Ready to explore ${activeTaxon.target_locus.gene_symbol} in BioDB`);
                          }
                        }}
                        className="flex items-center justify-center gap-1.5 border border-white/10 bg-[#162021] py-2 font-mono text-[10px] uppercase tracking-wider text-[#eee9de] transition hover:border-[#d5a65b]/50 hover:bg-[#d5a65b]/10 hover:text-[#f0c778]"
                      >
                        <Database size={12} />
                        Explore in BioDB
                      </button>

                      <button
                        onClick={() => {
                          if (onLoadInWorkbench) {
                            onLoadInWorkbench(
                              activeTaxon.target_locus.extinct_sequence_dna,
                              activeTaxon.target_locus.gene_symbol,
                              activeTaxon.scientific_name
                            );
                          } else {
                            toast.info(`Ready to load ${activeTaxon.target_locus.gene_symbol} into Sequence Workbench`);
                          }
                        }}
                        className="flex items-center justify-center gap-1.5 border border-white/10 bg-[#162021] py-2 font-mono text-[10px] uppercase tracking-wider text-[#eee9de] transition hover:border-[#4f9f96]/50 hover:bg-[#4f9f96]/10 hover:text-[#8cd1c7]"
                      >
                        <Dna size={12} />
                        Open in Workbench
                      </button>

                      <button
                        onClick={() => {
                          const prompt = `Analyze the adaptive paleogenomic substitutions in ${activeTaxon.scientific_name} (${activeTaxon.common_name}) ${activeTaxon.target_locus.gene_symbol} compared to extant ${activeTaxon.extant_counterpart.scientific_name}.`;
                          if (onAskInStudio) {
                            onAskInStudio(prompt, activeTaxon.scientific_name);
                          } else {
                            toast.info(`Prompt generated for Research Studio`);
                          }
                        }}
                        className="col-span-full flex items-center justify-center gap-1.5 border border-white/10 bg-[#162021] py-2 font-mono text-[10px] uppercase tracking-wider text-[#d5a65b] transition hover:border-[#d5a65b] hover:bg-[#d5a65b]/20"
                      >
                        <Microscope size={12} />
                        Query PaleoRAG Literature Studio
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Comparative Extant Relative Alignment */}
              {activeTab === "comparative" && comparisonStats && (
                <div className="mt-4 space-y-4">
                  {/* Pairwise Header */}
                  <div className="rounded border border-white/10 bg-black/40 p-3">
                    <div className="flex items-center justify-between text-xs">
                      <div>
                        <span className="font-mono text-[10px] text-slate-500 uppercase">Extinct Reference:</span>
                        <div className="font-serif italic font-semibold text-[#f0c778]">
                          {activeTaxon.scientific_name}
                        </div>
                      </div>
                      <ArrowRight size={14} className="text-slate-600" />
                      <div className="text-right">
                        <span className="font-mono text-[10px] text-slate-500 uppercase">Extant Sister:</span>
                        <div className="font-serif italic font-semibold text-[#8cd1c7]">
                          {activeTaxon.extant_counterpart.scientific_name}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 grid grid-cols-3 gap-2 border-t border-white/[0.06] pt-2 font-mono text-[10px]">
                      <div>
                        <div className="text-slate-500">Identity</div>
                        <div className="text-sm font-bold text-[#8cd1c7]">{comparisonStats.identityPct}%</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Divergence</div>
                        <div className="text-sm font-bold text-[#f0c778]">{comparisonStats.divergencePct}%</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Substitutions</div>
                        <div className="text-sm font-bold text-slate-200">{comparisonStats.diffs.length} AA</div>
                      </div>
                    </div>
                  </div>

                  {/* Pairwise Alignment Visualizer */}
                  <div>
                    <div className="mb-1.5 flex items-center justify-between font-mono text-[10px] text-slate-500">
                      <span>PROTEIN SEQUENCE ALIGNMENT (N-to-C TERMINUS)</span>
                      <button
                        onClick={() =>
                          copyToClipboard(
                            activeTaxon.target_locus.extinct_sequence_aa,
                            "aa"
                          )
                        }
                        className="flex items-center gap-1 text-[#d5a65b] hover:underline"
                      >
                        {copiedKey === "aa" ? <Check size={10} /> : <Copy size={10} />}
                        Copy AA FASTA
                      </button>
                    </div>

                    <div className="max-h-56 overflow-auto border border-white/10 bg-black/60 p-3 font-mono text-[11px] leading-relaxed">
                      <div className="flex gap-2">
                        <span className="w-16 shrink-0 text-slate-500">EXTINCT:</span>
                        <div className="break-all tracking-wider text-slate-300">
                          {activeTaxon.target_locus.extinct_sequence_aa.split("").map((ch: string, idx: number) => {
                            const isDiff =
                              idx < activeTaxon.extant_counterpart.extant_sequence_aa.length &&
                              ch !== activeTaxon.extant_counterpart.extant_sequence_aa[idx];
                            return (
                              <span
                                key={idx}
                                className={
                                  isDiff
                                    ? "bg-[#d5a65b]/30 font-bold text-[#f0c778] underline"
                                    : "text-slate-400"
                                }
                                title={`Residue ${idx + 1}: ${ch}`}
                              >
                                {ch}
                              </span>
                            );
                          })}
                        </div>
                      </div>

                      <div className="mt-2 flex gap-2">
                        <span className="w-16 shrink-0 text-slate-500">EXTANT:</span>
                        <div className="break-all tracking-wider text-slate-300">
                          {activeTaxon.extant_counterpart.extant_sequence_aa.split("").map((ch: string, idx: number) => {
                            const isDiff =
                              idx < activeTaxon.target_locus.extinct_sequence_aa.length &&
                              ch !== activeTaxon.target_locus.extinct_sequence_aa[idx];
                            return (
                              <span
                                key={idx}
                                className={
                                  isDiff
                                    ? "bg-[#4f9f96]/30 font-bold text-[#8cd1c7] underline"
                                    : "text-slate-500"
                                }
                                title={`Extant Residue ${idx + 1}: ${ch}`}
                              >
                                {ch}
                              </span>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Paleogenomic Substitutions Table */}
                  <div>
                    <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      Cataloged Amino Acid Substitutions & Functional Impacts
                    </div>
                    <div className="space-y-1.5 max-h-48 overflow-auto pr-1">
                      {activeTaxon.structure.mutations && activeTaxon.structure.mutations.length > 0 ? (
                        activeTaxon.structure.mutations.map((mut, idx) => (
                          <div
                            key={idx}
                            className="flex items-start justify-between rounded border border-white/[0.06] bg-black/30 p-2 text-xs"
                          >
                            <div className="flex items-center gap-2">
                              <span className="rounded bg-[#d5a65b]/20 px-1.5 py-0.5 font-mono text-[10px] font-bold text-[#f0c778]">
                                {mut.label || `${mut.ancestral_aa}${mut.position}${mut.derived_aa}`}
                              </span>
                              <span className="text-slate-300">{mut.functional_impact}</span>
                            </div>
                            {mut.grantham_distance && (
                              <span className="shrink-0 font-mono text-[9px] text-slate-500">
                                Grantham: {mut.grantham_distance}
                              </span>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="text-xs text-slate-500 italic">
                          No non-synonymous substitutions cataloged in the core coding sequence.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: 3D Structure */}
              {activeTab === "structure" && (
                <div className="mt-4 space-y-4">
                  <div className="flex items-center justify-between font-mono text-xs">
                    <div>
                      <span className="text-slate-500">RCSB PDB ID:</span>{" "}
                      <span className="font-bold text-[#f0c778]">{activeTaxon.structure.pdb_id}</span>
                    </div>
                    <div className="text-slate-400">
                      Resolution: {activeTaxon.structure.resolution_angstrom || "1.8"} Å
                    </div>
                  </div>

                  {/* 3D Molecular Viewer */}
                  <div className="border border-white/10 bg-black/60 p-1">
                    <MolecularViewer
                      pdbId={activeTaxon.structure.pdb_id}
                      title={activeTaxon.structure.title}
                      resolution={activeTaxon.structure.resolution_angstrom}
                      mutations={(activeTaxon.structure.mutations || []).map((m) => ({
                        position: m.position,
                        ancestral: m.ancestral_aa,
                        derived: m.derived_aa,
                        chain: "A",
                        functional_impact: m.functional_impact,
                      }))}
                      className="h-64 w-full"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 font-mono text-[10px]">
                    <div className="rounded border border-white/[0.06] bg-black/30 p-2">
                      <div className="text-slate-500 uppercase">CATH Code</div>
                      <div className="font-bold text-slate-200">
                        {activeTaxon.structure.cath_code || "1.10.490.10"}
                      </div>
                    </div>
                    <div className="rounded border border-white/[0.06] bg-black/30 p-2">
                      <div className="text-slate-500 uppercase">SCOP Fold</div>
                      <div className="font-bold text-slate-200">
                        {activeTaxon.structure.scop_fold || "Globin-like"}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <a
                      href={`https://www.rcsb.org/structure/${activeTaxon.structure.pdb_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 font-mono text-[10px] uppercase text-[#d5a65b] hover:underline"
                    >
                      View on RCSB PDB <ExternalLink size={10} />
                    </a>
                  </div>
                </div>
              )}

              {/* Tab 4: Genomics & KEGG */}
              {activeTab === "genomics" && (
                <div className="mt-4 space-y-4 text-xs">
                  <div>
                    <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      Chromosomal Synteny & Genomic Locus
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[11px]">
                      <div className="rounded border border-white/[0.06] bg-black/30 p-2">
                        <div className="text-[9px] uppercase text-slate-500">Chromosome</div>
                        <div className="font-bold text-slate-200">
                          {activeTaxon.genomics.chromosome}
                        </div>
                      </div>
                      <div className="rounded border border-white/[0.06] bg-black/30 p-2">
                        <div className="text-[9px] uppercase text-slate-500">Assembly</div>
                        <div className="font-bold text-slate-200">
                          {activeTaxon.genomics.assembly}
                        </div>
                      </div>
                      <div className="col-span-2 rounded border border-white/[0.06] bg-black/30 p-2">
                        <div className="text-[9px] uppercase text-slate-500">Coordinates (Start - End)</div>
                        <div className="font-bold text-[#8cd1c7]">
                          {activeTaxon.genomics.start.toLocaleString()} – {activeTaxon.genomics.end.toLocaleString()} bp
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <a
                      href={`https://genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&position=${activeTaxon.genomics.chromosome}:${activeTaxon.genomics.start}-${activeTaxon.genomics.end}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 flex items-center justify-center gap-1 border border-white/10 bg-black/40 py-2 font-mono text-[10px] uppercase text-[#eee9de] hover:border-[#d5a65b] hover:text-[#f0c778]"
                    >
                      UCSC Genome Browser <ExternalLink size={10} />
                    </a>
                    <a
                      href={`https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=${activeTaxon.target_locus.gene_symbol}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 flex items-center justify-center gap-1 border border-white/10 bg-black/40 py-2 font-mono text-[10px] uppercase text-[#eee9de] hover:border-[#4f9f96] hover:text-[#8cd1c7]"
                    >
                      Ensembl Synteny <ExternalLink size={10} />
                    </a>
                  </div>

                  <div className="border-t border-white/[0.06] pt-3">
                    <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      KEGG Metabolic / Disease Pathway
                    </div>
                    <div className="mt-2 rounded border border-white/10 bg-black/40 p-3">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] text-[#f0c778]">
                          {activeTaxon.pathway.kegg_id}
                        </span>
                        <a
                          href={`https://www.kegg.jp/entry/${activeTaxon.pathway.kegg_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-[10px] text-slate-400 hover:text-white"
                        >
                          KEGG Entry <ExternalLink size={9} className="inline" />
                        </a>
                      </div>
                      <div className="mt-1 font-semibold text-slate-200">
                        {activeTaxon.pathway.pathway_name}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="border border-dashed border-white/10 p-12 text-center text-sm text-slate-500">
              Select a taxon from the catalog to inspect its paleogenomic profile.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
