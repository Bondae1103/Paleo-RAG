import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Box,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Compass,
  Copy,
  Database,
  Dna,
  ExternalLink,
  FileText,
  Filter,
  Flame,
  GitBranch,
  Globe,
  Info,
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
  fetchTaxonProteins,
  fetchProteinDetails,
  fetchProteinRagSummary,
  TaxonRegistryEntry,
  TaxonProteinSummary,
  ProteinDetailsResponse,
  ProteinRagSummaryResponse,
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
  const [selectedSampleIndex, setSelectedSampleIndex] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<"overview" | "comparative" | "structure" | "genomics">("overview");
  const [selectedPdbId, setSelectedPdbId] = useState<string | null>(null);
  const [proteomeViewMode, setProteomeViewMode] = useState<"cards" | "table">("cards");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Staged Proteome & Relational Metadata State (Phase P9)
  const [proteomeLoading, setProteomeLoading] = useState(false);
  const [proteomeList, setProteomeList] = useState<TaxonProteinSummary[]>([]);
  const [proteomeFilter, setProteomeFilter] = useState("");
  const [reviewedOnlyFilter, setReviewedOnlyFilter] = useState(false);
  const [selectedProteinAcc, setSelectedProteinAcc] = useState<string | null>(null);
  const [proteinDetails, setProteinDetails] = useState<ProteinDetailsResponse | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [ragSummary, setRagSummary] = useState<ProteinRagSummaryResponse | null>(null);
  const [ragLoading, setRagLoading] = useState(false);

  // Load atlas catalog
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
            if (found) {
              setViewingTaxon(found);
              setSelectedSampleIndex(0);
            }
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

  // Load staged proteome for active taxon
  useEffect(() => {
    if (!viewingTaxon) {
      setProteomeList([]);
      setSelectedProteinAcc(null);
      setProteinDetails(null);
      setRagSummary(null);
      return;
    }
    let mounted = true;
    setProteomeLoading(true);
    fetchTaxonProteins(viewingTaxon.tax_id, 300).then((res) => {
      if (mounted && res) {
        setProteomeList(res.proteins);
        // Default select the active curated sample's accession if present in staged proteome, else first in list
        const activeSample = viewingTaxon.molecular_samples?.[selectedSampleIndex];
        const match = res.proteins.find((p) => p.accession === activeSample?.extinct_uniprot_acc);
        const defaultAcc = match ? match.accession : (res.proteins.length > 0 ? res.proteins[0].accession : null);
        setSelectedProteinAcc(defaultAcc);
      }
      if (mounted) setProteomeLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, [viewingTaxon, selectedSampleIndex]);

  // Load protein details & RAG explanation when selectedProteinAcc changes
  useEffect(() => {
    if (!selectedProteinAcc) {
      setProteinDetails(null);
      setRagSummary(null);
      return;
    }
    let mounted = true;
    setDetailsLoading(true);
    setRagLoading(true);

    fetchProteinDetails(selectedProteinAcc).then((res) => {
      if (mounted) {
        setProteinDetails(res);
        setDetailsLoading(false);
      }
    });

    fetchProteinRagSummary(selectedProteinAcc).then((res) => {
      if (mounted) {
        setRagSummary(res);
        setRagLoading(false);
      }
    });

    return () => {
      mounted = false;
    };
  }, [selectedProteinAcc]);

  // Filter clades and epochs
  const clades = useMemo(() => {
    const set = new Set<string>();
    taxa.forEach((t) => {
      const mainClade = t.clade.split(" ")[0].replace(/[^a-zA-Z]/g, "");
      if (mainClade) set.add(mainClade);
    });
    return ["All", ...Array.from(set).sort()];
  }, [taxa]);

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
    toast.success("Copied to clipboard");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Active molecular sample
  const activeSample = useMemo(() => {
    if (!viewingTaxon) return null;
    const samples = viewingTaxon.molecular_samples;
    if (samples && samples.length > 0) {
      return samples[selectedSampleIndex] || samples[0];
    }
    return {
      sample_id: `${viewingTaxon.tax_id}-SMP-01`,
      gene_symbol: viewingTaxon.target_locus.gene_symbol,
      protein_name: viewingTaxon.target_locus.protein_name,
      category: "Primary Diagnostic Marker",
      biological_significance: viewingTaxon.description,
      extinct_uniprot_acc: viewingTaxon.target_locus.extinct_uniprot_acc,
      extinct_nucleotide_acc: viewingTaxon.target_locus.extinct_nucleotide_acc,
      extinct_sequence_aa: viewingTaxon.target_locus.extinct_sequence_aa,
      extant_counterpart: viewingTaxon.extant_counterpart,
      structure: viewingTaxon.structure,
      genomics: viewingTaxon.genomics,
      pathway: viewingTaxon.pathway,
    };
  }, [viewingTaxon, selectedSampleIndex]);

  // Pairwise alignment
  const alignmentResult = useMemo(() => {
    if (!activeSample) return null;
    const extinct = proteinDetails?.sequence || activeSample.extinct_sequence_aa || "";
    const extant = activeSample.extant_counterpart.extant_sequence_aa || "";

    if (!extinct || !extant) return null;

    let matches = 0;
    let substitutions = 0;
    const maxLen = Math.max(extinct.length, extant.length);
    const alignedRows: Array<{
      pos: number;
      extinctChar: string;
      extantChar: string;
      isMatch: boolean;
      grantham?: number;
    }> = [];

    const distances: Record<string, number> = {
      TA: 58, AS: 99, EQ: 29, RG: 125, AV: 64, TI: 71,
      VM: 32, IL: 5, VI: 29, KR: 26, ML: 15, GA: 60,
    };
    const getGrantham = (a: string, b: string) => {
      if (a === b) return 0;
      const key = `${a}${b}`;
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
        grantham: getGrantham(eChar, xChar),
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
  }, [activeSample, proteinDetails]);

  // Filtered proteome list (with robust fallback to curated molecular samples)
  const filteredProteome = useMemo(() => {
    let list: TaxonProteinSummary[] = proteomeList;
    if (list.length === 0 && viewingTaxon?.molecular_samples) {
      list = viewingTaxon.molecular_samples.map((s, idx) => ({
        accession: s.extinct_uniprot_acc || `${viewingTaxon.tax_id}-LOC-${idx + 1}`,
        entry_name: s.gene_symbol,
        reviewed: true,
        protein_name: s.protein_name,
        gene_symbol: s.gene_symbol,
        sequence_length: s.extinct_sequence_aa ? s.extinct_sequence_aa.length : 0,
        exp_pdb_count: s.structure?.pdb_id ? 1 : 0,
        af_model_count: 0,
        paper_count: viewingTaxon.publications?.length || 0,
      }));
    }

    return list.filter((p) => {
      const matchesSearch =
        proteomeFilter.trim() === "" ||
        p.accession.toLowerCase().includes(proteomeFilter.toLowerCase()) ||
        p.gene_symbol.toLowerCase().includes(proteomeFilter.toLowerCase()) ||
        p.protein_name.toLowerCase().includes(proteomeFilter.toLowerCase()) ||
        p.entry_name.toLowerCase().includes(proteomeFilter.toLowerCase());

      const matchesReviewed = !reviewedOnlyFilter || p.reviewed;
      return matchesSearch && matchesReviewed;
    });
  }, [proteomeList, viewingTaxon, proteomeFilter, reviewedOnlyFilter]);

  // Active 3D viewer model calculation and provenance
  const activeViewerPdb = useMemo(() => {
    if (selectedPdbId) return selectedPdbId;
    if (proteinDetails?.experimental_structures && proteinDetails.experimental_structures.length > 0) {
      return proteinDetails.experimental_structures[0].pdb_id;
    }
    return activeSample?.structure?.pdb_id || null;
  }, [selectedPdbId, proteinDetails, activeSample]);

  const isAuthenticPdb = useMemo(() => {
    if (!activeViewerPdb) return false;
    return proteinDetails?.experimental_structures?.some(
      (s) => s.pdb_id.toUpperCase() === activeViewerPdb.toUpperCase()
    ) || false;
  }, [activeViewerPdb, proteinDetails]);

  // PBDB classic URL (Fix for 403 blocks per P9.3)
  const pbdbClassicUrl = useMemo(() => {
    if (!viewingTaxon?.fossil_record?.pbdb_taxon_id) return null;
    const cleanNo = viewingTaxon.fossil_record.pbdb_taxon_id.replace("txn:", "").trim();
    return cleanNo ? `https://paleobiodb.org/classic/checkTaxonInfo?taxon_no=${cleanNo}` : null;
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
              {pbdbClassicUrl && (
                <a
                  href={pbdbClassicUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 border border-[#70c4b5]/40 bg-[#70c4b5]/10 px-2.5 py-0.5 font-mono text-xs text-[#8cd1c7] hover:bg-[#70c4b5]/20"
                >
                  <span>PBDB: {t.fossil_record?.pbdb_taxon_id}</span>
                  <ExternalLink size={10} />
                </a>
              )}
            </div>
          </div>

          {/* DEDICATED HERO SECTION */}
          <section className="relative grid gap-8 border border-white/[0.08] bg-[#0e1315] p-6 lg:grid-cols-[1.1fr_0.9fr] lg:p-8">
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

                <div className="rounded border border-[#d5a65b]/30 bg-[#d5a65b]/[0.08] p-3 text-xs leading-relaxed text-slate-300">
                  <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider font-semibold text-[#f0c778]">
                    <Sparkles size={12} />
                    <span>Evolutionary Key Trait</span>
                  </div>
                  <div className="mt-1 text-sm font-semibold text-[#eee9de]">{t.key_trait}</div>
                  <p className="mt-1 text-xs text-slate-400 leading-normal">{t.description}</p>
                </div>

                {t.scope_note && (
                  <div className="rounded border border-[#70c4b5]/30 bg-[#70c4b5]/[0.08] p-3 text-xs leading-relaxed text-slate-300">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider font-semibold text-[#8cd1c7]">
                        <GitBranch size={12} />
                        <span>Taxonomic Clade Scope</span>
                      </div>
                      {t.included_species && t.included_species.length > 1 && (
                        <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 rounded bg-[#70c4b5]/20 text-[#8cd1c7] border border-[#70c4b5]/30">
                          {t.included_species.length} Species Represented
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-slate-300 leading-normal">{t.scope_note}</p>
                    {t.included_species && t.included_species.length > 1 && (
                      <div className="mt-2.5 pt-2 border-t border-white/[0.08]">
                        <span className="font-mono text-[10px] uppercase text-slate-400 block mb-1.5">
                          Represented Taxa &amp; Lineages:
                        </span>
                        <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto pr-1">
                          {t.included_species.map((sp: string) => (
                            <span key={sp} className="font-serif italic text-[11px] bg-black/40 border border-[#70c4b5]/25 px-2 py-0.5 rounded text-[#8cd1c7]">
                              {sp}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                  <div className="border border-white/[0.06] bg-black/20 p-2.5">
                    <span className="text-slate-500 block uppercase text-[10px]">Extinction Date</span>
                    <span className="text-slate-300 font-semibold">{t.extinction_date}</span>
                  </div>
                  <div className="border border-white/[0.06] bg-black/20 p-2.5">
                    <span className="text-slate-500 block uppercase text-[10px]">Extant Relative (H5)</span>
                    <span className="text-[#8cd1c7] italic">{t.extant_counterpart.scientific_name}</span>
                  </div>
                </div>
              </div>

              {/* ACTION BUTTONS */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-white/[0.08]">
                {onLoadInWorkbench && (
                  <button
                    onClick={() => onLoadInWorkbench(proteinDetails?.sequence || activeSample?.extinct_sequence_aa || t.target_locus.extinct_sequence_aa, activeSample?.gene_symbol || t.target_locus.gene_symbol, t.scientific_name)}
                    className="flex items-center gap-1.5 border border-[#70c4b5]/40 bg-[#70c4b5]/10 px-3.5 py-2 font-mono text-xs uppercase tracking-wider text-[#8cd1c7] hover:bg-[#70c4b5]/20"
                  >
                    <Dna size={13} />
                    <span>Workbench Alignment ({proteinDetails?.gene_symbol || activeSample?.gene_symbol || t.target_locus.gene_symbol})</span>
                  </button>
                )}

                {onExploreInBioDB && (
                  <button
                    onClick={() => onExploreInBioDB(proteinDetails?.gene_symbol || activeSample?.gene_symbol || t.target_locus.gene_symbol, t.scientific_name)}
                    className="flex items-center gap-1.5 border border-white/15 bg-white/[0.04] px-3.5 py-2 font-mono text-xs uppercase tracking-wider text-slate-300 hover:border-white/30 hover:text-white"
                  >
                    <Database size={13} />
                    <span>Query in BioDB</span>
                  </button>
                )}

                {onAskInStudio && (
                  <button
                    onClick={() => onAskInStudio(`What genetic adaptations enabled ${t.common_name} (${t.scientific_name}) to survive in its environment? Specifically regarding ${proteinDetails?.gene_symbol || activeSample?.gene_symbol || t.target_locus.gene_symbol} (${proteinDetails?.protein_name || activeSample?.protein_name || t.target_locus.protein_name}).`, t.scientific_name)}
                    className="flex items-center gap-1.5 border border-[#d5a65b]/40 bg-[#d5a65b]/10 px-3.5 py-2 font-mono text-xs uppercase tracking-wider text-[#f0c778] hover:bg-[#d5a65b]/20"
                  >
                    <Microscope size={13} />
                    <span>Ask Copilot</span>
                  </button>
                )}
              </div>
            </div>
          </section>

          {/* NATURAL HISTORY & ECOLOGICAL PROFILE (Strict hide-nulls enforced) */}
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
              <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                <Globe size={14} />
                <span>Paleontological &amp; Ecological Dossier</span>
              </div>
              <span className="font-mono text-[10px] text-slate-500">Natural History &amp; Stratigraphy</span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {t.habitat_range && (
                <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                  <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#f0c778]">
                    <MapPin size={14} />
                    <span>Where It Lived (Paleo-Habitat)</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-300">{t.habitat_range}</p>
                </div>
              )}

              <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#70c4b5]">
                  <Clock size={14} />
                  <span>Time Period &amp; Chronology</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-300">{t.geological_range || t.epoch}</p>
              </div>

              {t.diet_ecology && (
                <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                  <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#8cd1c7]">
                    <Compass size={14} />
                    <span>Diet &amp; Ecological Niche</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-300">{t.diet_ecology}</p>
                </div>
              )}

              {t.morphology && (
                <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                  <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#d5a65b]">
                    <Layers size={14} />
                    <span>Morphology &amp; Dimensions</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-300">{t.morphology}</p>
                </div>
              )}

              {t.extinction_driver && (
                <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                  <div className="flex items-center gap-2 font-mono text-xs font-semibold text-rose-400">
                    <ShieldAlert size={14} />
                    <span>Extinction Drivers</span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-300">{t.extinction_driver}</p>
                </div>
              )}

              {pbdbClassicUrl && (
                <div className="border border-white/[0.08] bg-[#0f1516] p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-mono text-xs font-semibold text-[#70c4b5]">
                      <Database size={14} />
                      <span>Paleobiology Database (PBDB)</span>
                    </div>
                    <a
                      href={pbdbClassicUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[#8cd1c7] hover:underline flex items-center gap-1 font-mono text-[10px]"
                    >
                      <span>Classic Record</span>
                      <ExternalLink size={10} />
                    </a>
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
              )}
            </div>
          </section>

          {/* TAXON PROTEOME & DIAGNOSTIC LOCI EXPLORER */}
          <section className="space-y-3 rounded border border-white/[0.08] bg-[#0c1214] p-4 lg:p-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
              <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                <Dna size={15} />
                <span className="font-semibold">Taxon Proteome &amp; Diagnostic Loci Explorer</span>
                <span className="text-[10px] font-normal text-slate-400 border-l border-white/10 pl-2">
                  {proteomeList.length || t.molecular_samples?.length || 0} Staged Proteins · {t.molecular_samples?.length || 0} Landmark Samples
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 text-slate-500" size={13} />
                  <input
                    type="text"
                    value={proteomeFilter}
                    onChange={(e) => setProteomeFilter(e.target.value)}
                    placeholder="Filter gene, accession, name..."
                    className="h-8 w-44 sm:w-60 border border-white/10 bg-black/40 pl-8 pr-3 font-mono text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-[#d5a65b]"
                  />
                  {proteomeFilter && (
                    <button
                      onClick={() => setProteomeFilter("")}
                      className="absolute right-2 top-2.5 text-slate-400 hover:text-white"
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>

                <button
                  onClick={() => setReviewedOnlyFilter(!reviewedOnlyFilter)}
                  className={`h-8 px-2.5 border font-mono text-[11px] transition rounded ${
                    reviewedOnlyFilter
                      ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300 font-semibold"
                      : "border-white/10 bg-black/20 text-slate-400 hover:text-white"
                  }`}
                  title="Filter Swiss-Prot reviewed proteins"
                >
                  {reviewedOnlyFilter ? "Reviewed (Swiss-Prot)" : "All (Swiss-Prot + TrEMBL)"}
                </button>

                <div className="flex items-center border border-white/10 rounded overflow-hidden">
                  <button
                    onClick={() => setProteomeViewMode("cards")}
                    className={`h-8 px-2.5 font-mono text-[11px] transition ${
                      proteomeViewMode === "cards"
                        ? "bg-[#d5a65b]/20 text-[#f0c778] font-semibold"
                        : "bg-black/20 text-slate-400 hover:text-white"
                    }`}
                  >
                    Landmark Cards
                  </button>
                  <button
                    onClick={() => setProteomeViewMode("table")}
                    className={`h-8 px-2.5 font-mono text-[11px] transition ${
                      proteomeViewMode === "table"
                        ? "bg-[#d5a65b]/20 text-[#f0c778] font-semibold"
                        : "bg-black/20 text-slate-400 hover:text-white"
                    }`}
                  >
                    Proteome Table ({filteredProteome.length})
                  </button>
                </div>
              </div>
            </div>

            {/* VIEW MODE 1: LANDMARK CARDS */}
            {proteomeViewMode === "cards" && (
              <div className="space-y-3">
                {t.molecular_samples && t.molecular_samples.length > 0 && (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    {t.molecular_samples.map((sample, sIdx) => {
                      const isSelected = selectedSampleIndex === sIdx || selectedProteinAcc === sample.extinct_uniprot_acc;
                      return (
                        <button
                          key={sample.sample_id || sIdx}
                          onClick={() => {
                            setSelectedSampleIndex(sIdx);
                            if (sample.extinct_uniprot_acc) {
                              setSelectedProteinAcc(sample.extinct_uniprot_acc);
                            }
                            setSelectedPdbId(null);
                          }}
                          className={`group flex flex-col justify-between text-left p-3.5 border transition rounded ${
                            isSelected
                              ? "border-[#d5a65b] bg-[#d5a65b]/[0.12] shadow-md shadow-black/40 ring-1 ring-[#d5a65b]/40"
                              : "border-white/[0.08] bg-black/25 hover:border-white/20 hover:bg-white/[0.03]"
                          }`}
                        >
                          <div className="space-y-1">
                            <div className="flex items-center justify-between">
                              <span className={`font-mono text-xs font-bold ${isSelected ? "text-[#f0c778]" : "text-white group-hover:text-[#eee9de]"}`}>
                                {sample.gene_symbol}
                              </span>
                              {sample.structure?.pdb_id && (
                                <span className="font-mono text-[9px] px-1.5 py-0.5 border rounded border-white/10 bg-black/40 text-[#8cd1c7]">
                                  PDB: {sample.structure.pdb_id}
                                </span>
                              )}
                            </div>
                            <div className="text-xs font-medium text-slate-200 line-clamp-1">
                              {sample.protein_name}
                            </div>
                            <div className="font-mono text-[10px] text-slate-400 line-clamp-1">
                              {sample.category}
                            </div>
                          </div>
                          <div className="mt-3 pt-2 border-t border-white/[0.06] flex items-center justify-between font-mono text-[9px]">
                            <span className="text-slate-500">{sample.structure?.mutations?.length || 0} diagnostic muts</span>
                            <span className={isSelected ? "text-[#f0c778] font-semibold" : "text-slate-500"}>
                              {isSelected ? "Active" : "Inspect →"}
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* QUICK ACCORDION OR STRIP FOR ALL OTHER MATCHING PROTEINS */}
                {filteredProteome.length > 0 && (
                  <div className="rounded border border-white/[0.06] bg-black/20 p-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                      <span className="text-slate-400">
                        {filteredProteome.length} Proteome Entries Available:
                      </span>
                      <button
                        onClick={() => setProteomeViewMode("table")}
                        className="text-[#8cd1c7] hover:underline flex items-center gap-1 text-[11px]"
                      >
                        <span>Open Full Searchable Table</span>
                        <ChevronRight size={12} />
                      </button>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-1">
                      {filteredProteome.slice(0, 40).map((p) => {
                        const isSelected = selectedProteinAcc === p.accession;
                        return (
                          <button
                            key={p.accession}
                            onClick={() => {
                              setSelectedProteinAcc(p.accession);
                              const sampleIdx = t.molecular_samples?.findIndex(
                                (s) => s.extinct_uniprot_acc === p.accession || s.gene_symbol === p.gene_symbol
                              );
                              if (sampleIdx !== undefined && sampleIdx >= 0) {
                                setSelectedSampleIndex(sampleIdx);
                              }
                              setSelectedPdbId(null);
                            }}
                            className={`font-mono text-[10px] px-2 py-1 rounded border transition flex items-center gap-1.5 ${
                              isSelected
                                ? "border-[#d5a65b] bg-[#d5a65b]/20 text-[#f0c778] font-bold"
                                : "border-white/10 bg-black/40 text-slate-300 hover:border-white/30 hover:text-white"
                            }`}
                          >
                            <span className="font-semibold">{p.gene_symbol}</span>
                            <span className="text-slate-500">({p.accession})</span>
                            {p.exp_pdb_count > 0 && <span className="text-teal-400 text-[9px]">PDB</span>}
                          </button>
                        );
                      })}
                      {filteredProteome.length > 40 && (
                        <button
                          onClick={() => setProteomeViewMode("table")}
                          className="font-mono text-[10px] px-2 py-1 rounded border border-[#d5a65b]/30 bg-[#d5a65b]/10 text-[#f0c778] hover:bg-[#d5a65b]/20"
                        >
                          +{filteredProteome.length - 40} more...
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* VIEW MODE 2: FULL SEARCHABLE PROTEOME TABLE */}
            {proteomeViewMode === "table" && (
              <div className="space-y-2">
                {proteomeLoading ? (
                  <div className="flex items-center gap-3 py-6 text-xs text-slate-400 font-mono">
                    <RotateCw className="animate-spin text-[#d5a65b]" size={16} />
                    <span>Loading proteome records from SQLite staging database...</span>
                  </div>
                ) : (
                  <div className="overflow-x-auto max-h-80 overflow-y-auto border border-white/[0.06] rounded">
                    <table className="w-full text-left font-mono text-xs">
                      <thead className="sticky top-0 bg-[#0f1516] text-slate-400 border-b border-white/[0.08] z-10">
                        <tr>
                          <th className="p-2.5">UniProt Accession</th>
                          <th className="p-2.5">Gene Symbol</th>
                          <th className="p-2.5">Protein Name</th>
                          <th className="p-2.5">Status</th>
                          <th className="p-2.5">Length</th>
                          <th className="p-2.5">3D Structures</th>
                          <th className="p-2.5">Literature</th>
                          <th className="p-2.5 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04] bg-black/20">
                        {filteredProteome.map((p) => {
                          const isSelected = selectedProteinAcc === p.accession;
                          const isLandmark = t.molecular_samples?.some(
                            (s) => s.extinct_uniprot_acc === p.accession || s.gene_symbol === p.gene_symbol
                          );
                          return (
                            <tr
                              key={p.accession}
                              onClick={() => {
                                setSelectedProteinAcc(p.accession);
                                const sampleIdx = t.molecular_samples?.findIndex(
                                  (s) => s.extinct_uniprot_acc === p.accession || s.gene_symbol === p.gene_symbol
                                );
                                if (sampleIdx !== undefined && sampleIdx >= 0) {
                                  setSelectedSampleIndex(sampleIdx);
                                }
                                setSelectedPdbId(null);
                              }}
                              className={`cursor-pointer transition ${
                                isSelected
                                  ? "bg-[#d5a65b]/15 border-l-2 border-[#d5a65b]"
                                  : "hover:bg-white/[0.03]"
                              }`}
                            >
                              <td className="p-2.5 font-bold">
                                <span className={isSelected ? "text-[#f0c778]" : "text-[#8cd1c7]"}>
                                  {p.accession}
                                </span>
                              </td>
                              <td className="p-2.5 font-semibold text-white">
                                <div className="flex items-center gap-1.5">
                                  <span>{p.gene_symbol}</span>
                                  {isLandmark && (
                                    <span className="font-mono text-[9px] px-1 py-0.2 rounded border border-[#d5a65b]/40 bg-[#d5a65b]/10 text-[#f0c778]">
                                      Landmark
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="p-2.5 text-slate-300 max-w-xs truncate" title={p.protein_name}>
                                {p.protein_name}
                              </td>
                              <td className="p-2.5">
                                <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                                  p.reviewed
                                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                                    : "border-amber-500/30 bg-amber-500/10 text-amber-300"
                                }`}>
                                  {p.reviewed ? "Reviewed" : "TrEMBL"}
                                </span>
                              </td>
                              <td className="p-2.5 text-slate-400">{p.sequence_length} aa</td>
                              <td className="p-2.5">
                                {p.exp_pdb_count > 0 ? (
                                  <span className="text-teal-300 font-bold">{p.exp_pdb_count} PDB</span>
                                ) : p.af_model_count > 0 ? (
                                  <span className="text-[#d5a65b]">AlphaFold</span>
                                ) : (
                                  <span className="text-slate-600">—</span>
                                )}
                              </td>
                              <td className="p-2.5">
                                {p.paper_count > 0 ? (
                                  <span className="text-[#8cd1c7]">{p.paper_count} papers</span>
                                ) : (
                                  <span className="text-slate-600">0</span>
                                )}
                              </td>
                              <td className="p-2.5 text-right">
                                <span className={`px-2 py-0.5 border rounded text-[10px] ${
                                  isSelected
                                    ? "border-[#d5a65b] bg-[#d5a65b]/20 text-[#f0c778] font-bold"
                                    : "border-white/10 text-slate-400 hover:text-white"
                                }`}>
                                  {isSelected ? "Active" : "Select"}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* ACTIVE PROTEIN INSPECTOR BANNER */}
          {selectedProteinAcc && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-[#70c4b5]/30 bg-[#70c4b5]/[0.06] p-3 text-xs">
              <div className="flex items-center gap-3">
                <span className="font-mono text-[10px] uppercase font-bold tracking-wider text-[#8cd1c7] px-2 py-0.5 border border-[#70c4b5]/30 bg-[#70c4b5]/10 rounded">
                  Inspecting Protein
                </span>
                <span className="font-mono font-bold text-white text-sm">
                  {proteinDetails?.accession || selectedProteinAcc}
                </span>
                <span className="text-slate-300 font-semibold">
                  {proteinDetails?.gene_symbol || activeSample?.gene_symbol} · {proteinDetails?.protein_name || activeSample?.protein_name}
                </span>
                {proteinDetails && (
                  <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${proteinDetails.reviewed ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-amber-500/20 text-amber-300 border border-amber-500/30"}`}>
                    {proteinDetails.reviewed ? "Swiss-Prot (Reviewed)" : "TrEMBL (Unreviewed)"}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 font-mono text-xs">
                {proteinDetails?.sequence_length && (
                  <span className="text-slate-400">{proteinDetails.sequence_length} aa</span>
                )}
                {proteinDetails?.experimental_structures?.length ? (
                  <span className="text-[#8cd1c7] border border-[#70c4b5]/30 px-2 py-0.5 bg-black/30 rounded">
                    {proteinDetails.experimental_structures.length} PDB Crystal Models
                  </span>
                ) : proteinDetails?.predicted_structures?.length ? (
                  <span className="text-[#d5a65b] border border-[#d5a65b]/30 px-2 py-0.5 bg-black/30 rounded">
                    AlphaFold DB Model (pLDDT {proteinDetails.predicted_structures[0].plddt_score})
                  </span>
                ) : null}
              </div>
            </div>
          )}

          {/* FUNCTIONAL DOSSIER TABS */}
          <section className="space-y-4">
            <div className="flex flex-wrap border-b border-white/[0.08] font-mono text-xs">
              <button
                onClick={() => setActiveTab("overview")}
                className={`flex items-center gap-2 border-b-2 px-4 py-2.5 transition ${
                  activeTab === "overview"
                    ? "border-[#d5a65b] font-semibold text-[#f0c778]"
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                <Activity size={14} />
                <span>Overview &amp; Literature Copilot</span>
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
                <span>Extant Relative Synteny &amp; Orthology</span>
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
                <span>3D Structure &amp; SIFTS Residues</span>
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

            {/* TAB CONTENT 1: OVERVIEW & RAG COPILOT */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                {/* RAG PALEOGENOMIC COPILOT PANEL */}
                <div className="rounded border border-[#d5a65b]/40 bg-[#0e1416] p-5 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
                    <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-[#f0c778] font-bold">
                      <Microscope size={16} />
                      <span>Grounded Literature Copilot // {proteinDetails?.gene_symbol || activeSample?.gene_symbol || t.target_locus.gene_symbol}</span>
                    </div>
                    <span className="font-mono text-[10px] text-slate-400">
                      PubMedBERT Hybrid Fusion · Grounded in Full-Text OA JATS Corpus
                    </span>
                  </div>

                  {ragLoading ? (
                    <div className="flex items-center gap-3 py-6 text-xs text-slate-400 font-mono">
                      <RotateCw className="animate-spin text-[#d5a65b]" size={16} />
                      <span>Synthesizing literature findings across paleogenomics corpus...</span>
                    </div>
                  ) : ragSummary ? (
                    ragSummary.abstention ? (
                      <div className="rounded border border-amber-500/30 bg-amber-500/10 p-4 text-xs font-mono text-amber-300 flex items-center gap-2">
                        <AlertTriangle size={15} />
                        <span>{ragSummary.explanation}</span>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="prose prose-invert max-w-none text-xs leading-relaxed text-slate-300 space-y-2 whitespace-pre-wrap font-sans">
                          {ragSummary.explanation}
                        </div>

                        {ragSummary.retrieved_chunks && ragSummary.retrieved_chunks.length > 0 && (
                          <div className="pt-3 border-t border-white/[0.06] space-y-2">
                            <span className="font-mono text-[10px] uppercase text-slate-400 block font-semibold">
                              Retrieved Literature Chunks ({ragSummary.retrieved_chunks.length} Supporting Spans):
                            </span>
                            <div className="grid gap-2 sm:grid-cols-2">
                              {ragSummary.retrieved_chunks.slice(0, 4).map((c, idx) => (
                                <div key={idx} className="border border-white/[0.06] bg-black/40 p-2.5 rounded space-y-1">
                                  <div className="flex items-center justify-between font-mono text-[9px]">
                                    <span className="text-[#8cd1c7] font-semibold">{c.doc_id}:{c.chunk_index}</span>
                                    <span className="text-slate-500">{c.section} · score {c.score.toFixed(4)}</span>
                                  </div>
                                  <p className="text-[11px] text-slate-400 line-clamp-3 leading-normal">
                                    {c.text}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  ) : (
                    <div className="text-xs text-slate-500 font-mono">
                      Select a protein from the catalog to load grounded paleogenomic findings.
                    </div>
                  )}
                </div>

                {/* GROUNDED PEER-REVIEWED LITERATURE PAPERS */}
                <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                    <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                      <BookOpen size={14} />
                      <span>Authoritative Peer-Reviewed Publications ({proteinDetails?.papers?.length || t.publications?.length || 0} Registered Papers)</span>
                    </div>
                    <span className="font-mono text-[10px] text-[#70c4b5]">
                      NCBI PubMed / Europe PMC Linked
                    </span>
                  </div>

                  {proteinDetails?.papers && proteinDetails.papers.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {proteinDetails.papers.map((pub, idx) => (
                        <div
                          key={pub.paper_id || idx}
                          className="border border-white/[0.06] bg-black/25 p-4 space-y-2 flex flex-col justify-between rounded"
                        >
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-[10px] text-[#d5a65b] font-semibold">
                                {pub.journal || "Journal Article"} ({pub.year || "N/A"})
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
                                {pub.pmid && (
                                  <a
                                    href={`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}/`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="font-mono text-[9px] text-slate-300 border border-white/10 px-1.5 py-0.5 rounded hover:text-white"
                                  >
                                    PMID:{pub.pmid}
                                  </a>
                                )}
                                {pub.is_open_access && (
                                  <span className="font-mono text-[9px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                                    Open Access
                                  </span>
                                )}
                              </div>
                            </div>
                            <h4 className="font-display text-sm font-semibold text-[#eee9de] leading-snug">
                              {pub.title}
                            </h4>
                            <div className="font-mono text-[10px] text-slate-500">
                              Evidence Type: <span className="text-[#8cd1c7]">{pub.evidence_type}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : t.publications && t.publications.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {t.publications.map((pub, idx) => (
                        <div
                          key={idx}
                          className="border border-white/[0.06] bg-black/25 p-4 space-y-2 flex flex-col justify-between rounded"
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
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500 font-mono">
                      No supporting literature registered for this locus.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB CONTENT 2: EXTANT RELATIVE SYNTENY & ORTHOLOGY */}
            {activeTab === "comparative" && activeSample && (
              <div className="space-y-6">
                {/* LIVING SISTER SPECIES SYNTENY BANNER (H5) */}
                <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
                    <div>
                      <div className="font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                        Living Sister Species Alignment (Decision H5)
                      </div>
                      <h3 className="font-display text-base text-[#eee9de]">
                        {t.common_name} ({t.scientific_name}) $\leftrightarrow$ {t.extant_counterpart.common_name} ({t.extant_counterpart.scientific_name})
                      </h3>
                    </div>
                    {proteinDetails?.orthology?.orthology_type && (
                      <span className="font-mono text-xs px-2.5 py-1 border rounded border-[#70c4b5]/30 bg-[#70c4b5]/10 text-[#8cd1c7]">
                        {proteinDetails.orthology.orthology_type.replace("_", " ")}
                      </span>
                    )}
                  </div>

                  {proteinDetails?.orthology?.status === "found" ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 font-mono text-xs">
                        <div className="border border-white/[0.06] bg-black/20 p-3">
                          <span className="text-slate-500 block uppercase text-[10px]">Extant Gene ID</span>
                          <span className="text-white font-semibold">{proteinDetails.orthology.extant_gene_id}</span>
                        </div>
                        <div className="border border-white/[0.06] bg-black/20 p-3">
                          <span className="text-slate-500 block uppercase text-[10px]">Ensembl Symbol</span>
                          <span className="text-[#8cd1c7] font-semibold">{proteinDetails.orthology.extant_gene_symbol}</span>
                        </div>
                        <div className="border border-white/[0.06] bg-black/20 p-3">
                          <span className="text-slate-500 block uppercase text-[10px]">Sequence Identity</span>
                          <span className="text-[#f0c778] font-semibold">{proteinDetails.orthology.identity_pct}%</span>
                        </div>
                        <div className="border border-white/[0.06] bg-black/20 p-3">
                          <span className="text-slate-500 block uppercase text-[10px]">Extinct Locus Status</span>
                          <span className="text-slate-400 font-semibold">{proteinDetails.orthology.extinct_coords_status}</span>
                        </div>
                      </div>

                      {proteinDetails.orthology.extant_chromosomal_coord && (
                        <div className="border border-white/[0.06] bg-black/30 p-3 font-mono text-xs space-y-1">
                          <span className="text-slate-500 block uppercase text-[10px]">Syntenic Chromosomal Coordinates (Ensembl)</span>
                          <span className="text-emerald-300 font-semibold">{proteinDetails.orthology.extant_chromosomal_coord}</span>
                        </div>
                      )}

                      {proteinDetails.orthology.extant_neighborhood && proteinDetails.orthology.extant_neighborhood.length > 0 && (
                        <div className="border border-white/[0.06] bg-black/30 p-4 space-y-2">
                          <span className="font-mono text-[10px] uppercase text-slate-400 block font-semibold">
                            Syntenic Flanking Gene Neighborhood ($\pm 50\text{ kb}$):
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {proteinDetails.orthology.extant_neighborhood.map((g, idx) => (
                              <div
                                key={idx}
                                className={`border px-3 py-2 rounded font-mono text-xs ${
                                  g.symbol === proteinDetails.orthology?.extant_gene_symbol
                                    ? "border-[#d5a65b] bg-[#d5a65b]/20 text-[#f0c778] font-bold"
                                    : "border-white/10 bg-black/40 text-slate-300"
                                }`}
                              >
                                <div className="text-sm">{g.symbol || g.gene_id}</div>
                                <div className="text-[10px] text-slate-500">
                                  {g.start}..{g.end} ({g.strand})
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="rounded border border-white/10 bg-black/30 p-4 text-xs font-mono text-slate-400 space-y-1">
                      <div className="text-[#f0c778] font-semibold">Syntenic Locus Status: Checked Not Found</div>
                      <p>
                        No chromosomal synteny block exists in the vertebrate reference (mitochondrial DNA encoded locus or unanchored ancient fragment). Source DB: NCBI_RefSeq, Ensembl.
                      </p>
                    </div>
                  )}
                </div>

                {/* PAIRWISE ALIGNMENT METRICS */}
                {alignmentResult && (
                  <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4">
                    <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                      <div className="font-mono text-xs uppercase tracking-wider text-[#70c4b5]">
                        Residue Matrix &amp; Pairwise Divergence: {activeSample.gene_symbol} ({alignmentResult.length} aa)
                      </div>
                      <div className="flex items-center gap-3 font-mono text-xs">
                        <span className="text-[#8cd1c7]">Identity: {alignmentResult.identityPct}%</span>
                        <span className="text-[#f0c778]">Divergence: {alignmentResult.divergencePct}%</span>
                      </div>
                    </div>

                    <div className="max-h-[260px] overflow-y-auto overflow-x-auto border border-white/[0.06] bg-black/40 p-3 font-mono text-xs">
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
                )}
              </div>
            )}

            {/* TAB CONTENT 3: 3D MOLECULAR STRUCTURE & SIFTS RESIDUES */}
            {activeTab === "structure" && activeSample && (
              <div className="space-y-6">
                {/* EXPERIMENTAL STRUCTURES TABLE (SIFTS RESIDUE RANGES) */}
                <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                    <div>
                      <div className="font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                        Authoritative Experimental PDB Structures (SIFTS Residue Mappings)
                      </div>
                      <h3 className="font-display text-base text-[#eee9de]">
                        RCSB PDB &amp; PDBe Verified Crystal Structures
                      </h3>
                    </div>
                    <span className="font-mono text-xs text-[#8cd1c7]">
                      {proteinDetails?.experimental_structures?.length || 0} Crystal Models
                    </span>
                  </div>

                  {proteinDetails?.experimental_structures && proteinDetails.experimental_structures.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left font-mono text-xs border border-white/[0.06]">
                        <thead className="bg-black/40 text-slate-400 border-b border-white/[0.08]">
                          <tr>
                            <th className="p-2.5">PDB ID</th>
                            <th className="p-2.5">Chain</th>
                            <th className="p-2.5">UniProt Range</th>
                            <th className="p-2.5">PDB Range</th>
                            <th className="p-2.5">Method</th>
                            <th className="p-2.5">Resolution</th>
                            <th className="p-2.5">Source</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.04]">
                          {proteinDetails.experimental_structures.map((s, idx) => {
                            const isCurrent = activeViewerPdb?.toUpperCase() === s.pdb_id.toUpperCase();
                            return (
                              <tr
                                key={idx}
                                onClick={() => setSelectedPdbId(s.pdb_id)}
                                className={`cursor-pointer transition ${isCurrent ? "bg-[#d5a65b]/10 border-l-2 border-[#d5a65b]" : "hover:bg-white/[0.02]"}`}
                              >
                                <td className="p-2.5 font-bold text-[#f0c778]">
                                  <div className="flex items-center gap-1.5">
                                    <span className="underline decoration-dotted">{s.pdb_id}</span>
                                    {isCurrent && (
                                      <span className="font-mono text-[9px] px-1 bg-[#d5a65b] text-black font-bold rounded">
                                        Active
                                      </span>
                                    )}
                                    <a
                                      href={`https://www.rcsb.org/structure/${s.pdb_id}`}
                                      target="_blank"
                                      rel="noreferrer"
                                      onClick={(e) => e.stopPropagation()}
                                      className="text-slate-400 hover:text-white"
                                    >
                                      <ExternalLink size={10} />
                                    </a>
                                  </div>
                                </td>
                                <td className="p-2.5 text-slate-300">{s.chain_id}</td>
                                <td className="p-2.5 text-emerald-400">
                                  {s.uniprot_start != null ? `${s.uniprot_start}–${s.uniprot_end}` : "N/A"}
                                </td>
                                <td className="p-2.5 text-teal-400">
                                  {s.pdb_start != null ? `${s.pdb_start}–${s.pdb_end}` : "N/A"}
                                </td>
                                <td className="p-2.5 text-slate-400">{s.method}</td>
                                <td className="p-2.5 text-[#8cd1c7]">
                                  {s.resolution ? `${s.resolution} Å` : "N/A"}
                                </td>
                                <td className="p-2.5 text-slate-500">{s.mapping_source}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="space-y-1.5 text-xs text-slate-300 font-mono p-3.5 bg-black/30 rounded border border-white/[0.08]">
                      <div className="flex items-center gap-2 text-amber-400 font-semibold">
                        <AlertTriangle size={14} />
                        <span>No Direct Extinct Organism Crystal Structure in RCSB PDB</span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-sans leading-relaxed">
                        Authentic prehistoric soft tissues typically cannot be crystallized directly. Per strict empirical standards, no direct crystal entries are attributed to this extinct organism. Below, the validated homologous modern reference structure ({activeSample?.structure?.pdb_id || "scaffold"}) is rendered as an empirical structural scaffold to project ancient substitutions.
                      </p>
                    </div>
                  )}

                  {/* PREDICTED STRUCTURES (ALPHAFOLD DB PER H7) */}
                  {proteinDetails?.predicted_structures && proteinDetails.predicted_structures.length > 0 && (
                    <div className="pt-3 border-t border-white/[0.06] space-y-3">
                      <div className="flex items-center justify-between font-mono text-xs">
                        <span className="text-[#d5a65b] font-semibold uppercase">
                          AlphaFold DB Supplementary Models (Decision H7)
                        </span>
                        <span className="text-slate-400 text-[10px]">
                          pLDDT Score: <strong className="text-emerald-400">{proteinDetails.predicted_structures[0].plddt_score}</strong>
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {proteinDetails.predicted_structures.map((af, idx) => (
                          <div key={idx} className="flex items-center gap-3 border border-white/10 bg-black/30 p-2.5 rounded font-mono text-xs">
                            <span className="font-bold text-white">{af.alphafold_id}</span>
                            <span className="text-slate-400">Type: {af.structure_type}</span>
                            <a
                              href={af.pdb_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[#8cd1c7] border border-[#70c4b5]/30 px-2 py-0.5 rounded hover:bg-[#70c4b5]/20 flex items-center gap-1"
                            >
                              <span>PDB</span>
                              <ExternalLink size={10} />
                            </a>
                            <a
                              href={af.cif_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[#f0c778] border border-[#d5a65b]/30 px-2 py-0.5 rounded hover:bg-[#d5a65b]/20 flex items-center gap-1"
                            >
                              <span>mmCIF</span>
                              <ExternalLink size={10} />
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 3D MOLECULAR VIEWER */}
                  {activeViewerPdb && (
                    <div className="space-y-3 pt-2">
                      <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-xs">
                        <div className="flex items-center gap-2">
                          <span className="text-slate-300">
                            Active 3D Model: <strong className="text-white text-sm">{activeViewerPdb}</strong>
                          </span>
                          {isAuthenticPdb ? (
                            <span className="font-mono text-[10px] px-2 py-0.5 rounded border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 font-semibold">
                              Authentic Extinct Crystal Structure
                            </span>
                          ) : (
                            <span className="font-mono text-[10px] px-2 py-0.5 rounded border border-amber-500/40 bg-amber-500/10 text-amber-300 font-semibold">
                              Homologous Reference Scaffold
                            </span>
                          )}
                        </div>
                        <div className="font-mono text-[11px] text-slate-400">
                          {activeSample?.structure?.mutations?.length || 0} ancient diagnostic mutations mapped
                        </div>
                      </div>

                      {!isAuthenticPdb && activeSample?.structure?.title && (
                        <div className="rounded border border-amber-500/20 bg-amber-500/[0.04] p-2.5 text-xs text-slate-300 font-sans flex items-start gap-2">
                          <Info size={14} className="text-amber-400 shrink-0 mt-0.5" />
                          <div className="space-y-0.5">
                            <span className="font-semibold text-amber-300">Homologous Modern Reference Scaffold: </span>
                            <span className="text-slate-200">{activeSample.structure.title}</span>
                            <span className="text-slate-400"> ({activeSample.structure.resolution_angstrom ? `${activeSample.structure.resolution_angstrom} Å` : "Cryo-EM / X-ray"}).</span>
                            <span className="text-slate-400 block text-[11px]">
                              Prehistoric biological tissues cannot typically be crystallized directly. Extinct-specific amino acid substitutions are projected onto this high-resolution extant homolog fold to visualize functional divergence.
                            </span>
                          </div>
                        </div>
                      )}

                      <div className="border border-white/10 bg-black/40 overflow-hidden rounded">
                        <MolecularViewer
                          pdbId={activeViewerPdb}
                          title={isAuthenticPdb ? `Authentic Experimental Structure PDB ${activeViewerPdb}` : activeSample?.structure?.title}
                          resolution={isAuthenticPdb ? proteinDetails?.experimental_structures?.find(s => s.pdb_id.toUpperCase() === activeViewerPdb.toUpperCase())?.resolution : activeSample?.structure?.resolution_angstrom}
                          mutations={activeSample?.structure?.mutations?.map((m) => ({
                            position: m.position,
                            ancestral: m.ancestral_aa,
                            derived: m.derived_aa,
                            chain: activeSample?.structure?.chain || "A",
                            functional_impact: m.functional_impact,
                          }))}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB CONTENT 4: FEDERATED BIOLOGICAL DBS */}
            {activeTab === "genomics" && (
              <div className="space-y-6">
                {/* 6 PRIMARY FEDERATED REPOSITORIES */}
                <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4 rounded">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
                    <div>
                      <div className="font-mono text-xs uppercase tracking-wider text-[#70c4b5] font-semibold">
                        Federated Cross-Database Accession Matrix // {proteinDetails?.gene_symbol || activeSample?.gene_symbol || t.target_locus.gene_symbol}
                      </div>
                      <h3 className="font-display text-base text-[#eee9de]">
                        6 Core Empirical Repositories Linked to {t.common_name} ({t.scientific_name})
                      </h3>
                    </div>
                    <span className="font-mono text-xs text-[#8cd1c7]">
                      6 Live Federated DBs
                    </span>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {/* NCBI Entrez */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2 rounded">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-[#f0c778] font-semibold">
                          NCBI Entrez
                        </span>
                        {activeSample?.extinct_nucleotide_acc && (
                          <a
                            href={`https://www.ncbi.nlm.nih.gov/nuccore/${activeSample.extinct_nucleotide_acc}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-white"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                      <div className={`font-mono text-xs ${activeSample?.extinct_nucleotide_acc ? "text-white font-bold" : "text-amber-500/80 italic"}`}>
                        {activeSample?.extinct_nucleotide_acc ?? "Unverified"}
                      </div>
                      <p className="text-[11px] text-slate-500">
                        {activeSample?.extinct_nucleotide_acc
                          ? "Official nucleotide sequence accession in GenBank."
                          : activeSample?.extinct_nucleotide_validation?.note ?? "No live NCBI Nucleotide record verifiably represents this organism/gene."}
                      </p>
                    </div>

                    {/* UniProtKB */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2 rounded">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-[#70c4b5] font-semibold">
                          UniProtKB
                        </span>
                        {(proteinDetails?.accession || activeSample?.extinct_uniprot_acc) && (
                          <a
                            href={`https://www.uniprot.org/uniprotkb/${proteinDetails?.accession || activeSample?.extinct_uniprot_acc}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-white"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                      <div className={`font-mono text-xs ${proteinDetails?.accession || activeSample?.extinct_uniprot_acc ? "text-white font-bold" : "text-amber-500/80 italic"}`}>
                        {(proteinDetails?.accession || activeSample?.extinct_uniprot_acc) ?? "Unverified"}
                      </div>
                      <p className="text-[11px] text-slate-500">
                        {proteinDetails?.reviewed
                          ? "Curated Swiss-Prot protein sequence with experimental functional annotation."
                          : activeSample?.extinct_uniprot_acc
                          ? "Curated protein sequence and functional annotation entry."
                          : activeSample?.extinct_uniprot_validation?.note ?? "No defensible UniProt match found for this organism/gene during live audit."}
                      </p>
                    </div>

                    {/* RCSB PDB */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2 rounded">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-[#8cd1c7] font-semibold">
                          RCSB PDB
                        </span>
                        {activeViewerPdb && (
                          <a
                            href={`https://www.rcsb.org/structure/${activeViewerPdb}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-white"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                      <div className="font-mono text-xs text-white font-bold">
                        {activeViewerPdb || "None mapped"}
                      </div>
                      <p className="text-[11px] text-slate-500">
                        {isAuthenticPdb
                          ? "Experimentally determined crystal structure of extinct organism."
                          : activeViewerPdb
                          ? `Validated homologous reference scaffold (${activeSample?.structure?.title || "extant relative"}).`
                          : "No empirical 3D coordinates registered."}
                      </p>
                    </div>

                    {/* KEGG Pathway */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2 rounded">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-300 font-semibold">
                          KEGG Pathway
                        </span>
                        {activeSample?.pathway?.kegg_id && (
                          <a
                            href={`https://www.kegg.jp/entry/${activeSample.pathway.kegg_id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-white"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                      <div className={`font-mono text-xs ${activeSample?.pathway?.kegg_id ? "text-white font-bold" : "text-amber-500/80 italic"}`}>
                        {activeSample?.pathway?.kegg_id ?? "Unverified"}
                      </div>
                      <p className="text-[11px] text-slate-500">
                        {activeSample?.pathway?.kegg_id
                          ? activeSample.pathway.pathway_name
                          : activeSample?.pathway?.kegg_validation?.note ?? "No live-confirmed KEGG pathway membership exists for this gene."}
                      </p>
                    </div>

                    {/* Ensembl Coordinates */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2 rounded">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-300 font-semibold">
                          Ensembl Coordinates
                        </span>
                        {activeSample?.genomics?.ensembl_species && activeSample?.genomics?.chromosome && (
                          <a
                            href={`https://www.ensembl.org/${activeSample.genomics.ensembl_species}/Location/View?r=${activeSample.genomics.chromosome.replace(/^chr/, "")}:${activeSample.genomics.start}-${activeSample.genomics.end}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-white"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                      {activeSample?.genomics?.chromosome ? (
                        <>
                          <div className="font-mono text-xs text-white font-bold">
                            {activeSample.genomics.chromosome}:{activeSample.genomics.start}..{activeSample.genomics.end}
                          </div>
                          <p className="text-[11px] text-slate-500">
                            Assembly: {activeSample.genomics.assembly} ({activeSample.genomics.ensembl_species})
                          </p>
                        </>
                      ) : (
                        <>
                          <div className="font-mono text-xs text-amber-500/80 italic">Unverified</div>
                          <p className="text-[11px] text-slate-500">
                            {activeSample?.genomics?.ensembl_validation?.note ?? "No live-verified Ensembl gene record exists for this organism."}
                          </p>
                        </>
                      )}
                    </div>

                    {/* Paleobiology Database */}
                    <div className="border border-white/[0.06] bg-black/25 p-3.5 space-y-2 rounded">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[11px] uppercase tracking-wider text-[#d5a65b] font-semibold">
                          PaleoBioDB
                        </span>
                        {pbdbClassicUrl && (
                          <a
                            href={pbdbClassicUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-white"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                      <div className="font-mono text-xs text-white font-bold">
                        {t.fossil_record?.pbdb_taxon_id ?? "Unverified"}
                      </div>
                      <p className="text-[11px] text-slate-500">
                        {t.fossil_record?.pbdb_taxon_id
                          ? `${t.fossil_record.fossil_occurrences_count ?? 0} fossil occurrences in Paleobiology Database.`
                          : "No live PBDB taxon identifier registered."}
                      </p>
                    </div>
                  </div>
                </div>

                {/* EXTENDED CROSS-REFERENCE REGISTRY (SQLITE & UNIPROT) */}
                {proteinDetails?.cross_references && Object.keys(proteinDetails.cross_references).length > 0 && (
                  <div className="border border-white/[0.08] bg-[#0f1516] p-5 space-y-4 rounded">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
                      <div>
                        <div className="font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
                          Extended Molecular Cross-References (SQLite Registered)
                        </div>
                        <h4 className="font-display text-sm text-[#eee9de]">
                          Secondary Genomic, Structural &amp; Functional Databases for {proteinDetails.gene_symbol} ({proteinDetails.accession})
                        </h4>
                      </div>
                      <span className="font-mono text-xs text-[#8cd1c7]">
                        {Object.keys(proteinDetails.cross_references).length} Secondary Databases
                      </span>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {Object.entries(proteinDetails.cross_references).map(([dbName, xrefs]) => (
                        <div key={dbName} className="border border-white/[0.06] bg-black/30 p-3.5 rounded space-y-2">
                          <div className="flex items-center justify-between font-mono text-xs border-b border-white/[0.06] pb-1.5">
                            <span className="font-bold text-[#f0c778]">{dbName}</span>
                            <span className="text-[10px] text-slate-500">{xrefs.length} xrefs</span>
                          </div>
                          <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                            {xrefs.map((x, idx) => (
                              <div key={idx} className="flex items-center justify-between font-mono text-xs">
                                <span className="text-slate-300 font-semibold">{x.identifier}</span>
                                {x.url && (
                                  <a
                                    href={x.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-[#8cd1c7] hover:underline flex items-center gap-1 text-[10px]"
                                  >
                                    <span>Link</span>
                                    <ExternalLink size={10} />
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    );
  }

  // ============================================================
  // RENDER MAIN TAXA ATLAS CATALOG GRID (18 TAXA)
  // ============================================================
  return (
    <div className="flex-1 overflow-y-auto px-5 py-6 md:px-10 md:py-8 space-y-8">
      <div className="mx-auto max-w-6xl space-y-8">
        {/* CATALOG HEADER & FILTER BAR */}
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-white/[0.08] pb-5">
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-[#d5a65b]">
              Paleogenomics Catalog / 18 Codified Taxa
            </div>
            <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-[#eee9de]">
              Prehistoric Taxa Atlas
            </h1>
            <p className="mt-1 text-xs text-slate-400">
              Select an extinct organism to inspect its verified proteome, SIFTS crystal structures, living sister synteny, and grounded RAG literature.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 text-slate-500" size={14} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search taxon, clade, trait..."
                className="h-9 w-64 border border-white/10 bg-black/40 pl-9 pr-3 font-mono text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-[#d5a65b]"
              />
            </div>

            <select
              value={selectedClade}
              onChange={(e) => setSelectedClade(e.target.value)}
              className="h-9 border border-white/10 bg-black/40 px-3 font-mono text-xs text-slate-300 outline-none focus:border-[#d5a65b]"
            >
              {clades.map((c) => (
                <option key={c} value={c} className="bg-[#0b0f10]">
                  Clade: {c}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 18 TAXA GRID */}
        {loading ? (
          <div className="flex items-center justify-center py-24 text-slate-400 font-mono text-xs gap-3">
            <RotateCw className="animate-spin text-[#d5a65b]" size={20} />
            <span>Loading Taxa Atlas Registry...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {filteredTaxa.map((t) => (
              <div
                key={t.tax_id}
                onClick={() => {
                  setViewingTaxon(t);
                  setSelectedSampleIndex(0);
                  setActiveTab("overview");
                }}
                className="group cursor-pointer rounded border border-white/[0.08] bg-[#0c1214] overflow-hidden transition duration-200 hover:border-[#d5a65b]/50 hover:bg-[#0f1719] hover:shadow-xl hover:shadow-black/50 flex flex-col justify-between"
              >
                <div>
                  <div className="relative aspect-[16/10] w-full overflow-hidden bg-black/60 border-b border-white/[0.06]">
                    {t.image_url ? (
                      <img
                        src={t.image_url}
                        alt={t.common_name}
                        className="h-full w-full object-cover object-center transition duration-300 group-hover:scale-105"
                      />
                    ) : (
                      <div className="grid h-full place-items-center font-mono text-xs text-slate-600">
                        No image available
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent pointer-events-none" />
                    <div className="absolute top-2.5 left-2.5 font-mono text-[9px] uppercase px-2 py-0.5 rounded border border-white/10 bg-black/70 text-[#d5a65b] font-bold">
                      {t.tax_id}
                    </div>
                    <div className="absolute bottom-2.5 left-2.5 right-2.5">
                      <h3 className="font-display text-lg font-bold text-[#eee9de] group-hover:text-[#f0c778] transition">
                        {t.common_name}
                      </h3>
                      <div className="font-serif italic text-xs text-[#8cd1c7]">
                        {t.scientific_name}
                      </div>
                    </div>
                  </div>

                  <div className="p-4 space-y-3">
                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {t.description}
                    </p>

                    <div className="grid grid-cols-2 gap-2 font-mono text-[10px] text-slate-400 pt-1 border-t border-white/[0.06]">
                      <div>
                        <span className="text-slate-600 block">CLADE</span>
                        <span className="text-slate-300 font-medium truncate block">{t.clade}</span>
                      </div>
                      <div>
                        <span className="text-slate-600 block">EPOCH</span>
                        <span className="text-slate-300 font-medium truncate block">{t.epoch}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="p-4 pt-0">
                  <div className="flex items-center justify-between border-t border-white/[0.06] pt-3 font-mono text-[10px]">
                    <span className="text-[#8cd1c7]">
                      {t.molecular_samples?.length || 1} Curated Loci
                    </span>
                    <span className="text-[#d5a65b] group-hover:translate-x-0.5 transition flex items-center gap-1 font-semibold">
                      Inspect Dossier →
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
