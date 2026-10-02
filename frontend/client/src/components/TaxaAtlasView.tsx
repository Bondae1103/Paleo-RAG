import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowLeft,
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
  Globe,
  Layers,
  MapPin,
  Microscope,
  Network,
  RotateCw,
  Search,
  ShieldAlert,
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
  initialTaxonId?: string | null;
  onExploreInBioDB?: (query: string, organism: string) => void;
  onLoadInWorkbench?: (sequence: string, locus: string, organism: string) => void;
  onAskInStudio?: (prompt: string, taxon: string) => void;
}

export const TaxaAtlasView: React.FC<TaxaAtlasViewProps> = ({
  initialTaxonId,
  onExploreInBioDB,
  onLoadInWorkbench,
  onAskInStudio,
}) => {
  const [taxa, setTaxa] = useState<TaxonRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedClade, setSelectedClade] = useState<string>("All");
  const [selectedEpoch, setSelectedEpoch] = useState<string>("All");
  const [viewingTaxon, setViewingTaxon] = useState<TaxonRegistryEntry | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "comparative" | "structure" | "genomics" | "fossils">("overview");
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
          if (initialTaxonId) {
            const found = list.find((t) => t.tax_id === initialTaxonId || t.common_name.toLowerCase().includes(initialTaxonId.toLowerCase()));
            if (found) setViewingTaxon(found);
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
  }, [initialTaxonId]);

  // Unique clades and epochs for filter bars
  const clades = useMemo(() => {
    const set = new Set<string>();
    taxa.forEach((t) => {
      const mainClade = t.clade.split(" ")[0].replace(/[^a-zA-Z]/g, "");
      if (mainClade) set.add(mainClade);
    });
    return ["All", ...Array.from(set).sort()];
  }, [taxa]);

  // Filtered taxa based on search, clade, and epoch
  const filteredTaxa = useMemo(() => {
    return taxa.filter((t) => {
      const matchesSearch =
        searchQuery.trim() === "" ||
        t.common_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.scientific_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.tax_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.key_trait.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.target_locus.gene_symbol.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesClade =
        selectedClade === "All" ||
        t.clade.toLowerCase().includes(selectedClade.toLowerCase());

      const matchesEpoch =
        selectedEpoch === "All" ||
        t.epoch.toLowerCase().includes(selectedEpoch.toLowerCase());

      return matchesSearch && matchesClade && matchesEpoch;
    });
  }, [taxa, searchQuery, selectedClade, selectedEpoch]);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success("Copied accession to clipboard");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Pairwise Alignment Computation between Extinct and Extant Sequences
  const alignmentResult = useMemo(() => {
    if (!viewingTaxon) return null;
    const extinct = viewingTaxon.target_locus.extinct_sequence_aa || "";
    const extant = viewingTaxon.extant_counterpart.extant_sequence_aa || "";

    if (!extinct || !extant) return null;

    let matches = 0;
    let substitutions = 0;
    const minLen = Math.min(extinct.length, extant.length);
    const maxLen = Math.max(extinct.length, extant.length);
    const alignedRows: Array<{
      pos: number;
      extinctChar: string;
      extantChar: string;
      isMatch: boolean;
      grantham?: number;
    }> = [];

    // Grantham distance table approximation
    const getGrantham = (a: string, b: string) => {
      if (a === b) return 0;
      const key = `${a}${b}`;
      const distances: Record<string, number> = {
        TA: 58, AS: 99, EQ: 29, RG: 125, AV: 64, TI: 71,
        VM: 32, IL: 5, VI: 29, KR: 26, ML: 15, GA: 60,
      };
      return distances[key] || distances[`${b}${a}`] || 45;
    };

    for (let i = 0; i < maxLen; i++) {
      const eChar = extinct[i] || "-";
      const xChar = extant[i] || "-";
      const isMatch = eChar === xChar && eChar !== "-";
      if (isMatch) matches++;
      else if (eChar !== "-" && xChar !== "-") substitutions++;

      alignedRows.push({
        pos: i + 1,
        extinctChar: eChar,
        extantChar: xChar,
        isMatch,
        grantham: eChar !== "-" && xChar !== "-" && !isMatch ? getGrantham(eChar, xChar) : 0,
      });
    }

    const identityPct = maxLen > 0 ? ((matches / maxLen) * 100).toFixed(1) : "0.0";
    const divergencePct = maxLen > 0 ? (((maxLen - matches) / maxLen) * 100).toFixed(1) : "0.0";

    return {
      rows: alignedRows,
      identityPct,
      divergencePct,
      matches,
      substitutions,
      length: maxLen,
    };
  }, [viewingTaxon]);

  // ============================================================
  // RENDER DEDICATED FULL-PAGE ANIMAL DOSSIER
  // ============================================================
  if (viewingTaxon) {
    const t = viewingTaxon;
    return (
      <div className="flex-1 overflow-y-auto px-5 py-6 md:px-10 md:py-8 space-y-8">
        <div className="mx-auto max-w-6xl space-y-8">
          {/* BACK NAVIGATION BAR */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
            <button
              onClick={() => setViewingTaxon(null)}
              className="inline-flex items-center gap-2 border border-white/10 bg-white/[0.03] px-3.5 py-1.5 font-mono text-xs uppercase tracking-[0.14em] text-slate-300 transition hover:border-[#d5a65b] hover:bg-[#d5a65b]/10 hover:text-[#f0c778]"
            >
              <ArrowLeft size={14} />
              <span>Back to Taxa Atlas (18 Taxa)</span>
            </button>

            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-slate-500">{t.tax_id}</span>
              <span className="border border-[#d5a65b]/40 bg-[#d5a65b]/10 px-2.5 py-0.5 font-mono text-xs text-[#f0c778]">
                {t.clade}
              </span>
              {t.fossil_record?.pbdb_taxon_id && (
                <a
                  href={t.fossil_record.pbdb_navigator_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 border border-[#70c4b5]/40 bg-[#70c4b5]/10 px-2.5 py-0.5 font-mono text-xs text-[#8cd1c7] hover:bg-[#70c4b5]/20"
                >
                  <span>PBDB: {t.fossil_record.pbdb_taxon_id}</span>
                  <ExternalLink size={10} />
                </a>
              )}
            </div>
          </div>

          {/* DEDICATED HERO SECTION */}
          <section className="relative grid gap-8 border border-white/[0.08] bg-[#0e1315] p-6 lg:grid-cols-[1.1fr_0.9fr] lg:p-8">
            {/* LEFT: FULL-WIDTH UNRESOLVED LIFE RESTORATION PHOTO */}
            <div className="space-y-2">
              <div className="relative aspect-[16/10] w-full overflow-hidden rounded border border-white/10 bg-[#080c0d]">
                {t.image_url ? (
                  <img
                    src={t.image_url}
                    alt={t.common_name}
                    className="h-full w-full object-cover object-center"
                  />
                ) : (
                  <div className="grid h-full place-items-center font-mono text-xs text-slate-600">
                    No life reconstruction image available
                  </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent pointer-events-none" />
              </div>
              {t.image_caption && (
                <p className="font-mono text-[11px] leading-relaxed text-slate-400 italic px-1">
                  {t.image_caption}
                </p>
              )}
            </div>

            {/* RIGHT: TAXON IDENTITY & QUICK ACTIONS */}
            <div className="flex flex-col justify-between space-y-6">
              <div className="space-y-4">
                <div>
                  <div className="font-mono text-xs text-[#d5a65b] uppercase tracking-wider">
                    {t.clade} · {t.tax_id}
                  </div>
                  <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-[#eee9de] sm:text-4xl">
                    {t.common_name}
                  </h1>
                  <div className="font-serif italic text-lg text-[#8cd1c7]">
                    {t.scientific_name}
                  </div>
                </div>

                {/* Key Adaptation Tag */}
                <div className="rounded border border-[#d5a65b]/30 bg-[#d5a65b]/[0.08] p-3 text-xs leading-relaxed text-slate-300">
                  <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider font-semibold text-[#f0c778]">
                    <Sparkles size={12} />
                    <span>Evolutionary Key Trait</span>
                  </div>
                  <div className="mt-1 text-sm font-semibold text-[#eee9de]">{t.key_trait}</div>
                  <p className="mt-1 text-xs text-slate-400 leading-normal">{t.description}</p>
                </div>

                {/* Quick Metadata Row */}
                <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                  <div className="border border-white/[0.06] bg-black/20 p-2.5">
                    <span className="text-slate-500 block uppercase text-[10px]">Extinction Date</span>
                    <span className="text-slate-300 font-semibold">{t.extinction_date}</span>
                  </div>
                  <div className="border border-white/[0.06] bg-black/20 p-2.5">
                    <span className="text-slate-500 block uppercase text-[10px]">Extant Relative</span>
                    <span className="text-[#8cd1c7] italic">{t.extant_counterpart.scientific_name}</span>
                  </div>
                </div>
              </div>

              {/* ACTION LAUNCH BUTTONS */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-white/[0.08]">
                {onLoadInWorkbench && (
                  <button
                    onClick={() => onLoadInWorkbench(t.target_locus.extinct_sequence_aa, t.target_locus.gene_symbol, t.scientific_name)}
                    className="flex items-center gap-1.5 border border-[#70c4b5]/40 bg-[#70c4b5]/10 px-3.5 py-2 font-mono text-xs uppercase tracking-wider text-[#8cd1c7] hover:bg-[#70c4b5]/20"
                  >
                    <Dna size={13} />
                    <span>Workbench Alignment</span>
                  </button>
                )}

                {onExploreInBioDB && (
                  <button
                    onClick={() => onExploreInBioDB(t.target_locus.gene_symbol, t.scientific_name)}
                    className="flex items-center gap-1.5 border border-white/15 bg-white/[0.04] px-3.5 py-2 font-mono text-xs uppercase tracking-wider text-slate-300 hover:border-white/30 hover:text-white"
                  >
                    <Database size={13} />
                    <span>Query in BioDB</span>
                  </button>
                )}

                {onAskInStudio && (
                  <button
                    onClick={() => onAskInStudio(`What genetic adaptations enabled ${t.common_name} (${t.scientific_name}) to survive in its environment?`, t.scientific_name)}
                    className="flex items-center gap-1.5 border border-[#d5a65b]/40 bg-[#d5a65b]/10 px-3.5 py-2 font-mono text-xs uppercase tracking-wider text-[#f0c778] hover:bg-[#d5a65b]/20"
                  >
                    <Microscope size={13} />
                    <span>Ask Copilot</span>
                  </button>
                )}
              </div>
            </div>
          </section>

          {/* RICH PALEONTOLOGICAL & ECOLOGICAL PROFILE (FILLS THE SPACE NATURALLY) */}
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
              <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                <Globe size={14} />
                <span>Paleontological &amp; Ecological Dossier</span>
              </div>
              <span className="font-mono text-[10px] text-slate-500">Natural History &amp; Stratigraphy</span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {/* HABITAT & GEOGRAPHIC RANGE */}
              <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#f0c778]">
                  <MapPin size={14} />
                  <span>Where It Lived (Paleo-Habitat)</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-300">
                  {t.habitat_range || "Pleistocene glacial and interglacial steppe environments across northern latitudes."}
                </p>
              </div>

              {/* TIME PERIOD & CHRONOLOGY */}
              <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#70c4b5]">
                  <Clock size={14} />
                  <span>Time Period &amp; Chronology</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-300">
                  {t.geological_range || t.epoch}
                </p>
              </div>

              {/* DIET & ECOLOGICAL NICHE */}
              <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#8cd1c7]">
                  <Compass size={14} />
                  <span>Diet &amp; Ecological Niche</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-300">
                  {t.diet_ecology || "Specialized niche occupying apex trophic levels within the Pleistocene megafaunal ecosystem."}
                </p>
              </div>

              {/* PHYSICAL TRAITS & MORPHOLOGY */}
              <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#d5a65b]">
                  <Layers size={14} />
                  <span>Morphology &amp; Dimensions</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-300">
                  {t.morphology || "High skeletal bone density and adapted cranial architecture reflecting sub-zero thermal selection."}
                </p>
              </div>

              {/* EXTINCTION CAUSALITY */}
              <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-rose-400">
                  <ShieldAlert size={14} />
                  <span>Extinction Drivers</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-300">
                  {t.extinction_driver || "Post-glacial climatic restructuring, habitat fragmentation, and human predatory pressure."}
                </p>
              </div>

              {/* FOSSIL OCCURRENCES FROM PBDB */}
              <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#70c4b5]">
                    <Database size={14} />
                    <span>Paleobiology Database (PBDB)</span>
                  </div>
                  {t.fossil_record?.pbdb_navigator_url && (
                    <a
                      href={t.fossil_record.pbdb_navigator_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[#8cd1c7] hover:underline flex items-center gap-1 font-mono text-[10px]"
                    >
                      <span>Navigator</span>
                      <ExternalLink size={10} />
                    </a>
                  )}
                </div>
                <div className="text-xs text-slate-300 space-y-1">
                  <div>Occurrences: <strong className="text-white font-mono">{t.fossil_record?.fossil_occurrences_count ?? 0} collections</strong></div>
                  <div>Geological Interval: <span className="text-slate-400 font-mono">{t.fossil_record?.geological_interval || "Pleistocene"}</span></div>
                  {t.fossil_record?.first_appearance_ma && (
                    <div className="text-[11px] text-slate-500 font-mono">
                      First: {t.fossil_record.first_appearance_ma} Ma · Last: {t.fossil_record.last_appearance_ma} Ma
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* FUNCTIONAL DOSSIER TABS */}
          <section className="space-y-4">
            <div className="flex border-b border-white/[0.08] font-mono text-xs">
              <button
                onClick={() => setActiveTab("overview")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 transition ${
                  activeTab === "overview"
                    ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                <Activity size={14} />
                <span>Overview &amp; Literature</span>
              </button>

              <button
                onClick={() => setActiveTab("comparative")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 transition ${
                  activeTab === "comparative"
                    ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                <GitBranch size={14} />
                <span>Extant Relative Synteny</span>
              </button>

              <button
                onClick={() => setActiveTab("structure")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 transition ${
                  activeTab === "structure"
                    ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                <Box size={14} />
                <span>3D Molecular Structure</span>
              </button>

              <button
                onClick={() => setActiveTab("genomics")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 transition ${
                  activeTab === "genomics"
                    ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                <Network size={14} />
                <span>Federated Biological DBs</span>
              </button>
            </div>

            {/* TAB CONTENT 1: OVERVIEW & LITERATURE */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                {/* GROUNDED PEER-REVIEWED LITERATURE */}
                <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                    <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                      <BookOpen size={14} />
                      <span>Grounded Paleogenomic Publications (Literature Copilot Corpus)</span>
                    </div>
                    <span className="font-mono text-[10px] text-[#70c4b5]">
                      {t.publications?.length || 0} Peer-Reviewed Landmark Papers
                    </span>
                  </div>

                  {t.publications && t.publications.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {t.publications.map((pub, idx) => (
                        <div
                          key={idx}
                          className="border border-white/[0.06] bg-black/25 p-4 space-y-2 flex flex-col justify-between"
                        >
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-[10px] text-[#d5a65b] font-semibold">
                                {pub.journal} ({pub.year})
                              </span>
                              <div className="flex items-center gap-1.5">
                                {pub.pmcid && (
                                  <a
                                    href={`https://www.ncbi.nlm.nih.gov/pmc/articles/${pub.pmcid}/`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="font-mono text-[9px] text-[#8cd1c7] border border-[#70c4b5]/30 bg-[#70c4b5]/10 px-1.5 py-0.5 rounded hover:bg-[#70c4b5]/20"
                                  >
                                    {pub.pmcid}
                                  </a>
                                )}
                                {pub.doi && (
                                  <a
                                    href={`https://doi.org/${pub.doi}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="font-mono text-[9px] text-slate-400 border border-white/10 px-1.5 py-0.5 rounded hover:text-white"
                                  >
                                    DOI
                                  </a>
                                )}
                              </div>
                            </div>
                            <h4 className="font-display text-sm font-semibold text-[#eee9de] leading-snug">
                              {pub.title}
                            </h4>
                            <div className="font-mono text-[10px] text-slate-500">{pub.authors}</div>
                            <p className="text-xs text-slate-400 leading-relaxed pt-1">
                              {pub.summary}
                            </p>
                          </div>

                          {onAskInStudio && (
                            <button
                              onClick={() =>
                                onAskInStudio(
                                  `Based on ${pub.authors} (${pub.year}, ${pub.journal}), what are the key paleogenomic findings for ${t.common_name}?`,
                                  t.scientific_name
                                )
                              }
                              className="mt-3 flex items-center justify-between border border-white/10 bg-black/30 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-[#f0c778] hover:border-[#d5a65b] hover:bg-[#d5a65b]/10"
                            >
                              <span>Ask Copilot about this paper</span>
                              <ChevronRight size={11} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No linked publications in corpus.</p>
                  )}
                </div>
              </div>
            )}

            {/* TAB CONTENT 2: EXTANT SYNTEY */}
            {activeTab === "comparative" && alignmentResult && (
              <div className="space-y-6">
                {/* ALIGNMENT METRICS STRIP */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 border border-white/[0.08] bg-[#0f1516] p-4">
                  <div className="border border-white/[0.06] bg-black/20 p-3">
                    <span className="font-mono text-[10px] uppercase text-slate-500 block">Sequence Identity</span>
                    <span className="font-mono text-xl font-bold text-[#70c4b5]">{alignmentResult.identityPct}%</span>
                    <span className="text-[11px] text-slate-500 block">{alignmentResult.matches} identical residues</span>
                  </div>

                  <div className="border border-white/[0.06] bg-black/20 p-3">
                    <span className="font-mono text-[10px] uppercase text-slate-500 block">Sequence Divergence</span>
                    <span className="font-mono text-xl font-bold text-[#d5a65b]">{alignmentResult.divergencePct}%</span>
                    <span className="text-[11px] text-slate-500 block">{alignmentResult.substitutions} substitutions</span>
                  </div>

                  <div className="border border-white/[0.06] bg-black/20 p-3">
                    <span className="font-mono text-[10px] uppercase text-slate-500 block">Extinct Taxon</span>
                    <span className="text-xs font-semibold text-[#eee9de] block truncate">{t.common_name}</span>
                    <span className="font-mono text-[10px] text-slate-500 block">{t.target_locus.extinct_uniprot_acc}</span>
                  </div>

                  <div className="border border-white/[0.06] bg-black/20 p-3">
                    <span className="font-mono text-[10px] uppercase text-slate-500 block">Living Relative</span>
                    <span className="text-xs font-semibold text-[#8cd1c7] italic block truncate">{t.extant_counterpart.scientific_name}</span>
                    <span className="font-mono text-[10px] text-slate-500 block">{t.extant_counterpart.extant_uniprot_acc}</span>
                  </div>
                </div>

                {/* SUBSTITUTION CARDS */}
                {t.structure.mutations && t.structure.mutations.length > 0 && (
                  <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-3">
                    <div className="font-mono text-xs uppercase tracking-wider text-[#d5a65b] font-semibold">
                      Diagnostic Derived Amino Acid Substitutions
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {t.structure.mutations.map((m, idx) => (
                        <div key={idx} className="border border-white/[0.06] bg-black/30 p-3 space-y-1.5">
                          <div className="flex items-center justify-between font-mono">
                            <span className="text-sm font-bold text-[#f0c778]">{m.label}</span>
                            <span className="text-[10px] text-slate-400">Position {m.position}</span>
                          </div>
                          <div className="text-[11px] text-slate-300">
                            Ancestral <strong className="text-rose-400">{m.ancestral_aa}</strong> → Derived <strong className="text-[#70c4b5]">{m.derived_aa}</strong>
                          </div>
                          <div className="text-[10px] text-slate-400 font-mono">
                            Grantham Distance: {m.grantham_distance}
                          </div>
                          <p className="text-[11px] text-slate-400 leading-normal pt-1 border-t border-white/[0.06]">
                            {m.functional_impact}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* FULL SEQUENCE COMPARISON VIEW */}
                <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="font-mono text-xs uppercase tracking-wider text-[#70c4b5]">
                      Aligned Residue Matrix ({alignmentResult.length} aa)
                    </div>
                    <span className="font-mono text-[10px] text-slate-500">Green = Match · Gold = Mismatch</span>
                  </div>
                  <div className="max-h-[300px] overflow-y-auto overflow-x-auto border border-white/[0.06] bg-black/40 p-3 font-mono text-xs">
                    <div className="flex flex-wrap gap-1">
                      {alignmentResult.rows.map((r) => (
                        <div
                          key={r.pos}
                          title={`Pos ${r.pos}: Extinct=${r.extinctChar} vs Extant=${r.extantChar}${r.isMatch ? " (Match)" : ` (Mismatch, Grantham ${r.grantham})`}`}
                          className={`w-6 h-9 flex flex-col items-center justify-center rounded border text-[10px] ${
                            r.isMatch
                              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                              : "border-[#d5a65b]/60 bg-[#d5a65b]/20 text-[#f0c778] font-bold"
                          }`}
                        >
                          <span>{r.extinctChar}</span>
                          <span className="text-[8px] text-slate-500">{r.extantChar}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB CONTENT 3: 3D MOLECULAR STRUCTURE */}
            {activeTab === "structure" && (
              <div className="space-y-6">
                <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                    <div>
                      <div className="font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                        3D Coordinate Modeling &amp; Residue Mapping
                      </div>
                      <h3 className="font-display text-base text-[#eee9de]">
                        {t.structure.title} (RCSB PDB: {t.structure.pdb_id})
                      </h3>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-xs">
                      <span className="border border-white/10 bg-black/30 px-2 py-0.5 text-slate-400">
                        Chain {t.structure.chain}
                      </span>
                      <span className="border border-[#70c4b5]/30 bg-[#70c4b5]/10 px-2 py-0.5 text-[#8cd1c7]">
                        Resolution: {t.structure.resolution_angstrom} Å
                      </span>
                    </div>
                  </div>

                  {/* 3DMOL VIEWER CONTAINER (EXPANSIVE) */}
                  <div className="border border-white/10 bg-black/40 overflow-hidden rounded">
                    <MolecularViewer
                      pdbId={t.structure.pdb_id}
                      title={t.structure.title}
                      resolution={t.structure.resolution_angstrom}
                      mutations={t.structure.mutations?.map((m) => ({
                        position: m.position,
                        ancestral: m.ancestral_aa,
                        derived: m.derived_aa,
                        chain: t.structure.chain || "A",
                        functional_impact: m.functional_impact,
                      }))}
                    />
                  </div>

                  {/* STRUCTURAL ANNOTATIONS */}
                  <div className="grid gap-3 sm:grid-cols-2 pt-2 font-mono text-xs">
                    <div className="border border-white/[0.06] bg-black/25 p-3">
                      <span className="text-slate-500 block uppercase text-[10px]">CATH Architecture Code</span>
                      <span className="text-[#8cd1c7] font-semibold">{t.structure.cath_code || "1.20.120.30"}</span>
                    </div>
                    <div className="border border-white/[0.06] bg-black/25 p-3">
                      <span className="text-slate-500 block uppercase text-[10px]">SCOP Structural Fold</span>
                      <span className="text-[#f0c778] font-semibold">{t.structure.scop_fold || "Globin-like / Multi-helical fold"}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB CONTENT 4: FEDERATED DATABASES */}
            {activeTab === "genomics" && (
              <div className="space-y-6">
                <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                    <div className="font-mono text-xs uppercase tracking-wider text-[#70c4b5]">
                      Federated Cross-Database Accession Matrix
                    </div>
                    <span className="font-mono text-[10px] text-slate-500">6 External Repositories</span>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {/* NCBI Entrez */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-[#f0c778] font-semibold">NCBI Entrez</span>
                        <a
                          href={`https://www.ncbi.nlm.nih.gov/nuccore/${t.target_locus.extinct_nucleotide_acc}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-400 hover:text-white"
                        >
                          <ExternalLink size={12} />
                        </a>
                      </div>
                      <div className="font-mono text-xs text-white">{t.target_locus.extinct_nucleotide_acc}</div>
                      <p className="text-[11px] text-slate-500">Official nucleotide sequence accession in GenBank.</p>
                    </div>

                    {/* UniProt */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-[#70c4b5] font-semibold">UniProtKB</span>
                        <a
                          href={`https://www.uniprot.org/uniprotkb/${t.target_locus.extinct_uniprot_acc}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-400 hover:text-white"
                        >
                          <ExternalLink size={12} />
                        </a>
                      </div>
                      <div className="font-mono text-xs text-white">{t.target_locus.extinct_uniprot_acc}</div>
                      <p className="text-[11px] text-slate-500">Curated protein sequence and functional annotation entry.</p>
                    </div>

                    {/* RCSB PDB */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-[#8cd1c7] font-semibold">RCSB PDB</span>
                        <a
                          href={`https://www.rcsb.org/structure/${t.structure.pdb_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-400 hover:text-white"
                        >
                          <ExternalLink size={12} />
                        </a>
                      </div>
                      <div className="font-mono text-xs text-white">{t.structure.pdb_id}</div>
                      <p className="text-[11px] text-slate-500">Experimentally determined 3D atomic coordinates.</p>
                    </div>

                    {/* KEGG Pathway */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-300 font-semibold">KEGG Pathway</span>
                        <a
                          href={`https://www.kegg.jp/entry/${t.pathway.kegg_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-400 hover:text-white"
                        >
                          <ExternalLink size={12} />
                        </a>
                      </div>
                      <div className="font-mono text-xs text-white">{t.pathway.kegg_id}</div>
                      <p className="text-[11px] text-slate-500">{t.pathway.pathway_name}</p>
                    </div>

                    {/* Ensembl Species */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-300 font-semibold">Ensembl Species</span>
                        <a
                          href={`https://www.ensembl.org/${t.genomics.ensembl_species}/`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-400 hover:text-white"
                        >
                          <ExternalLink size={12} />
                        </a>
                      </div>
                      <div className="font-mono text-xs text-white">{t.genomics.chromosome}:{t.genomics.start}..{t.genomics.end}</div>
                      <p className="text-[11px] text-slate-500">Assembly: {t.genomics.assembly}</p>
                    </div>

                    {/* Paleobiology Database */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-[#d5a65b] font-semibold">PaleoBioDB</span>
                        {t.fossil_record?.pbdb_navigator_url && (
                          <a
                            href={t.fossil_record.pbdb_navigator_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-white"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                      <div className="font-mono text-xs text-white">{t.fossil_record?.pbdb_taxon_id || "Uncataloged"}</div>
                      <p className="text-[11px] text-slate-500">Stratigraphic occurrences: {t.fossil_record?.fossil_occurrences_count || 0}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    );
  }

  // ============================================================
  // RENDER CATALOG GRID VIEW (ALL 18 TAXA)
  // ============================================================
  return (
    <div className="flex-1 overflow-y-auto px-5 py-6 md:px-10 md:py-8 space-y-8">
      <div className="mx-auto max-w-6xl space-y-8">
        {/* HEADER & FILTER BAR */}
        <section className="space-y-4 border-b border-white/[0.08] pb-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[#d5a65b]">
                <BookOpen size={12} />
                <span>Prehistoric Species Registry // 18 Codified Taxa</span>
              </div>
              <h1 className="mt-1 font-display text-2xl font-bold text-[#eee9de] sm:text-3xl">
                Taxa Atlas &amp; Evolutionary Registry
              </h1>
              <p className="mt-1 text-xs text-slate-400 max-w-2xl">
                Explore codified prehistoric genomes, authentic life restorations, pairwise synteny against living sister taxa,
                3D cold-adapted molecular structures, and deep-time fossil occurrences.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="border border-white/10 bg-black/40 px-3 py-1.5 font-mono text-xs text-[#8cd1c7]">
                {filteredTaxa.length} / {taxa.length} Taxa Loaded
              </span>
            </div>
          </div>

          {/* SEARCH & CLADE FILTERS */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            {/* Search Input */}
            <div className="relative min-w-[240px] flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by taxon name, gene locus (HBB, MC1R), or trait..."
                className="w-full border border-white/10 bg-black/30 py-2 pl-9 pr-8 font-mono text-xs text-slate-200 placeholder:text-slate-600 focus:border-[#d5a65b]/60 focus:outline-none"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                >
                  <X size={12} />
                </button>
              )}
            </div>

            {/* Clade Pills */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-mono text-[10px] uppercase text-slate-500 mr-1 flex items-center gap-1">
                <Filter size={11} /> Clade:
              </span>
              {clades.map((clade) => (
                <button
                  key={clade}
                  onClick={() => setSelectedClade(clade)}
                  className={`px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider transition ${
                    selectedClade === clade
                      ? "border border-[#d5a65b] bg-[#d5a65b]/15 text-[#f0c778]"
                      : "border border-white/[0.08] bg-black/20 text-slate-400 hover:border-white/20 hover:text-white"
                  }`}
                >
                  {clade}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* 18 TAXA CATALOG GRID (UNCROPPED 16:10 IMAGES) */}
        {loading ? (
          <div className="border border-white/10 bg-[#0f1516] p-16 text-center">
            <RotateCw size={24} className="mx-auto animate-spin text-[#d5a65b]" />
            <p className="mt-3 font-mono text-xs uppercase tracking-wider text-slate-400">Loading Prehistoric Registry...</p>
          </div>
        ) : filteredTaxa.length === 0 ? (
          <div className="border border-dashed border-white/10 p-12 text-center text-sm text-slate-500">
            No prehistoric taxa matched your search query.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {filteredTaxa.map((item) => (
              <div
                key={item.tax_id}
                onClick={() => setViewingTaxon(item)}
                className="group flex flex-col justify-between border border-white/[0.08] bg-[#0f1516] transition hover:border-[#d5a65b]/60 hover:shadow-xl hover:shadow-black/50 cursor-pointer overflow-hidden rounded"
              >
                <div>
                  {/* UNRESOLVED, NATURAL 16:10 LIFE RESTORATION IMAGE HEADER */}
                  <div className="relative aspect-[16/10] w-full overflow-hidden bg-[#080c0d] border-b border-white/[0.08]">
                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        alt={item.common_name}
                        className="h-full w-full object-cover object-center transition-transform duration-500 group-hover:scale-105"
                        loading="lazy"
                      />
                    ) : (
                      <div className="grid h-full place-items-center font-mono text-[10px] text-slate-600">
                        Life restoration pending
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-[#0f1516] via-transparent to-black/30 pointer-events-none" />

                    {/* Image Header Badges */}
                    <div className="absolute top-2.5 left-2.5">
                      <span className="rounded border border-white/15 bg-black/70 px-2 py-0.5 font-mono text-[10px] font-semibold text-[#f0c778] backdrop-blur-sm">
                        {item.tax_id}
                      </span>
                    </div>

                    <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5">
                      <span className="rounded border border-white/15 bg-black/70 px-2 py-0.5 font-mono text-[9px] text-slate-300 backdrop-blur-sm">
                        {item.clade}
                      </span>
                      {item.fossil_record?.pbdb_taxon_id && (
                        <span className="rounded border border-[#70c4b5]/40 bg-[#70c4b5]/20 px-2 py-0.5 font-mono text-[9px] text-[#8cd1c7] backdrop-blur-sm">
                          PBDB
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Card Content */}
                  <div className="p-4 space-y-3">
                    <div>
                      <h3 className="font-display text-lg font-semibold text-[#eee9de] group-hover:text-white transition">
                        {item.common_name}
                      </h3>
                      <div className="font-serif italic text-xs text-[#8cd1c7]">
                        {item.scientific_name}
                      </div>
                    </div>

                    {/* Key Trait */}
                    <div className="rounded bg-white/[0.03] p-2.5 text-xs space-y-1">
                      <div className="font-mono text-[10px] uppercase font-semibold text-[#f0c778] flex items-center gap-1">
                        <Sparkles size={11} /> {item.key_trait}
                      </div>
                      <p className="text-slate-400 line-clamp-2 text-[11px] leading-relaxed">
                        {item.description}
                      </p>
                    </div>

                    {/* Target Locus & Extant Relative */}
                    <div className="grid grid-cols-2 gap-2 border-t border-white/[0.06] pt-2.5 font-mono text-[10px]">
                      <div>
                        <span className="text-slate-500 uppercase block text-[9px]">Target Gene</span>
                        <span className="text-[#eee9de] font-semibold">{item.target_locus.gene_symbol}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 uppercase block text-[9px]">Extant Relative</span>
                        <span className="text-slate-300 italic truncate block">{item.extant_counterpart.scientific_name}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card Action Footer */}
                <div className="border-t border-white/[0.06] bg-black/20 px-4 py-2.5 flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-slate-400 group-hover:text-[#f0c778] transition">
                  <span>{item.extinction_date}</span>
                  <span className="flex items-center gap-1 font-semibold text-[#f0c778]">
                    <span>Open Dossier</span>
                    <ArrowRight size={12} className="transition-transform group-hover:translate-x-1" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
