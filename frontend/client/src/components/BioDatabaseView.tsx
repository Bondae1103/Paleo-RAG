import React, { useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  Box,
  CircleCheck,
  Compass,
  Database,
  Dna,
  ExternalLink,
  GitBranch,
  Layers,
  Network,
  RotateCw,
  Search,
  Share2,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import {
  BioLookupResponse,
  fetchInteractions,
  fetchStructureMutations,
  lookupBio,
  scanMotifs,
} from "../lib/api";
import { MolecularViewer } from "./MolecularViewer";

interface CaseStudyPreset {
  label: string;
  query: string;
  organism: string;
  nucleotide: string;
  protein: string;
  pdb: string;
  pfam: string;
  prosite: string;
  description: string;
}

const CASE_STUDIES: CaseStudyPreset[] = [
  {
    label: "Mammoth HBB",
    query: "HBB",
    organism: "Mammuthus primigenius",
    nucleotide: "HQ184444.1",
    protein: "D3U1H9",
    pdb: "3VRF",
    pfam: "PF00042",
    prosite: "PS01033",
    description:
      "Cold-adaptation substitutions in woolly mammoth hemoglobin reducing enthalpy of oxygenation for arctic survival.",
  },
  {
    label: "Neanderthal FOXP2",
    query: "FOXP2",
    organism: "Homo neanderthalensis",
    nucleotide: "AF512946.1",
    protein: "O15409",
    pdb: "2A07",
    pfam: "PF00250",
    prosite: "PS00658",
    description:
      "Speech/language associated forkhead transcription factor shared identically between archaic Neanderthals and modern humans.",
  },
  {
    label: "Ancient Y. pestis Pla",
    query: "Pla",
    organism: "Yersinia pestis",
    nucleotide: "AL590842.1",
    protein: "P17811",
    pdb: "2X55",
    pfam: "PF01278",
    prosite: "PS00834",
    description:
      "Plasminogen activator protease on pPCP1 virulence plasmid essential for pneumonic plague dissemination across Bronze Age/Black Death lineages.",
  },
];

export const BioDatabaseView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("HBB");
  const [searchOrganism, setSearchOrganism] = useState("Mammuthus primigenius");
  const [loading, setLoading] = useState(false);
  const [record, setRecord] = useState<BioLookupResponse | null>(null);
  const [selectedCaseStudy, setSelectedCaseStudy] = useState<string>("Mammoth HBB");

  // Structure & Mutations state
  const [mutations, setMutations] = useState<any[]>([]);

  // STRING filter state
  const [stringScoreMin, setStringScoreMin] = useState(400);

  // Motif Scanner interactive state
  const [scanInputSeq, setScanInputSeq] = useState("");
  const [scanResults, setScanResults] = useState<any[]>([]);
  const [scanning, setScanning] = useState(false);

  const executeLookup = async (q: string, org?: string) => {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const data = await lookupBio(q.trim(), org?.trim() || undefined);
      setRecord(data);

      // If structure record present, load mutations
      if (data.structure_record?.pdb_id) {
        try {
          const muts = await fetchStructureMutations(data.structure_record.pdb_id);
          setMutations(muts.mutations || []);
        } catch {
          setMutations([]);
        }
      } else {
        setMutations([]);
      }

      // If protein sequence present, pre-fill motif scanner
      if (data.protein_record?.sequence) {
        setScanInputSeq(data.protein_record.sequence);
      }

      toast.success(`Cross-referenced biological databases for ${q}`);
    } catch (err: any) {
      toast.error(`Lookup error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCaseStudy = (cs: CaseStudyPreset) => {
    setSelectedCaseStudy(cs.label);
    setSearchQuery(cs.query);
    setSearchOrganism(cs.organism);
    executeLookup(cs.query, cs.organism);
  };

  const handleMotifScan = async () => {
    if (!scanInputSeq.trim()) return;
    setScanning(true);
    try {
      const res = await scanMotifs(scanInputSeq.trim());
      setScanResults(res.matches || []);
      toast.success(`Found ${res.matches.length} motif signature match(es)`);
    } catch (err: any) {
      toast.error(`Motif scan error: ${err.message}`);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto bg-[#0b0f10] p-4 md:p-8">
      {/* Heading */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.24em] text-[#79bcb3]">
            <span className="h-px w-5 bg-[#79bcb3]" />
            Modules 2–6 · Multi-Database Mining & Cross-Referencing (CO2–CO5)
          </div>
          <h1 className="font-display text-2xl font-semibold tracking-[-0.03em] text-[#eee9de] md:text-3xl">
            Biological Databases Explorer
          </h1>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-400">
            Federated queries across INSDC (NCBI/ENA/DDBJ), UniProtKB, RCSB PDB, CATH/SCOP, Pfam, PROSITE, KEGG,
            STRING, Ensembl, and UCSC Genome Browser.
          </p>
        </div>

        {/* Case Studies Badges */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-[10px] uppercase text-slate-500">Case Studies:</span>
          {CASE_STUDIES.map((cs) => (
            <button
              key={cs.label}
              onClick={() => handleSelectCaseStudy(cs)}
              className={`border px-2.5 py-1 font-mono text-[11px] transition ${
                selectedCaseStudy === cs.label
                  ? "border-[#d5a65b] bg-[#d5a65b]/20 text-[#f0c778]"
                  : "border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/20 hover:text-slate-200"
              }`}
            >
              {cs.label}
            </button>
          ))}
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-6 border border-white/[0.08] bg-[#0e1314] p-4">
        <div className="grid gap-3 sm:grid-cols-[1.5fr_1fr_auto]">
          <div>
            <label className="block font-mono text-[9px] uppercase tracking-wider text-slate-500 mb-1">
              Query (Gene symbol, Accession, or PDB ID)
            </label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") executeLookup(searchQuery, searchOrganism);
                }}
                className="h-9 w-full border border-white/10 bg-black/40 pl-9 pr-3 font-mono text-xs text-slate-200 outline-none focus:border-[#4f9f96]/60"
                placeholder="e.g. HBB, FOXP2, Pla, D3U1H9, 3VRF..."
              />
            </div>
          </div>

          <div>
            <label className="block font-mono text-[9px] uppercase tracking-wider text-slate-500 mb-1">
              Organism Filter (Optional)
            </label>
            <input
              value={searchOrganism}
              onChange={(e) => setSearchOrganism(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") executeLookup(searchQuery, searchOrganism);
              }}
              className="h-9 w-full border border-white/10 bg-black/40 px-3 font-mono text-xs text-slate-200 outline-none focus:border-[#4f9f96]/60"
              placeholder="e.g. Mammuthus primigenius, Homo neanderthalensis..."
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={() => executeLookup(searchQuery, searchOrganism)}
              disabled={loading}
              className="flex h-9 items-center gap-1.5 bg-[#d5a65b] px-4 font-mono text-xs font-semibold uppercase tracking-wider text-[#17130d] transition hover:bg-[#f0c778] disabled:opacity-50"
            >
              {loading ? <RotateCw size={13} className="animate-spin" /> : <Search size={13} />}
              Query All DBs
            </button>
          </div>
        </div>
      </div>

      {/* Main Results Container */}
      {!record && !loading && (
        <div className="border border-dashed border-white/10 p-12 text-center">
          <Database size={32} className="mx-auto text-slate-600 mb-3" />
          <div className="font-mono text-sm text-slate-400">No database query executed yet</div>
          <p className="mt-1 text-xs text-slate-600">
            Click one of the verified paleogenomic case studies above or enter a gene/accession to query the live biological databases.
          </p>
        </div>
      )}

      {loading && (
        <div className="border border-white/10 bg-[#0e1314] p-12 text-center">
          <RotateCw size={28} className="mx-auto animate-spin text-[#d5a65b] mb-3" />
          <div className="font-mono text-xs uppercase tracking-wider text-slate-300">
            Federating query across NCBI, UniProt, RCSB PDB, Pfam, KEGG, STRING, and Ensembl...
          </div>
        </div>
      )}

      {record && !loading && (
        <div className="space-y-6">
          {/* Top Overview Strip */}
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
            <div className="border border-white/[0.08] bg-[#0e1314] p-4">
              <span className="block font-mono text-[10px] uppercase text-slate-500">Query Target</span>
              <span className="font-display text-lg font-semibold text-[#eee9de]">{record.query}</span>
              {record.organism && (
                <span className="block text-xs italic text-slate-400">{record.organism}</span>
              )}
            </div>
            <div className="border border-white/[0.08] bg-[#0e1314] p-4">
              <span className="block font-mono text-[10px] uppercase text-slate-500">NCBI / ENA Nucleotide</span>
              <span className="font-display text-lg font-semibold text-[#70c4b5]">
                {record.nucleotide_record?.id || "N/A"}
              </span>
              <span className="block font-mono text-[10px] text-slate-500">
                {record.nucleotide_record ? `${record.nucleotide_record.length} bp` : "No direct accession"}
              </span>
            </div>
            <div className="border border-white/[0.08] bg-[#0e1314] p-4">
              <span className="block font-mono text-[10px] uppercase text-slate-500">UniProtKB / Swiss-Prot</span>
              <span className="font-display text-lg font-semibold text-[#f0c778]">
                {record.protein_record?.accession || "N/A"}
              </span>
              <span className="block font-mono text-[10px] text-slate-500">
                {record.protein_record ? `${record.protein_record.length} aa` : "No protein record"}
              </span>
            </div>
            <div className="border border-white/[0.08] bg-[#0e1314] p-4">
              <span className="block font-mono text-[10px] uppercase text-slate-500">RCSB PDB Structure</span>
              <span className="font-display text-lg font-semibold text-[#8cd1c7]">
                {record.structure_record?.pdb_id || "N/A"}
              </span>
              <span className="block font-mono text-[10px] text-slate-500">
                {record.structure_record?.resolution_angstrom
                  ? `${record.structure_record.resolution_angstrom.toFixed(2)} Å (${record.structure_record.method})`
                  : "No coordinate model"}
              </span>
            </div>
          </div>

          {/* Dual Column Layout: Left Column = DB details, Right Column = 3D viewer & Network */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Left Column: Nucleotide + UniProt + Domains + Pathways */}
            <div className="space-y-6">
              {/* Card 1: INSDC Nucleotide Record */}
              {record.nucleotide_record && (
                <div className="border border-white/[0.08] bg-[#0e1314] p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Dna size={15} className="text-[#70c4b5]" />
                      <span className="font-mono text-xs font-semibold uppercase text-slate-200">
                        Primary Nucleotide DB (INSDC / NCBI E-utilities)
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <a
                        href={`https://www.ncbi.nlm.nih.gov/nuccore/${record.nucleotide_record.id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 font-mono text-[10px] text-[#70c4b5] hover:underline"
                      >
                        NCBI <ExternalLink size={10} />
                      </a>
                      <a
                        href={`https://www.ebi.ac.uk/ena/browser/view/${record.nucleotide_record.id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 font-mono text-[10px] text-slate-400 hover:text-white"
                      >
                        ENA <ExternalLink size={10} />
                      </a>
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <span className="font-mono text-slate-500">Accession: </span>
                      <span className="font-mono text-[#eee9de]">{record.nucleotide_record.id}</span>
                    </div>
                    <div>
                      <span className="font-mono text-slate-500">Definition: </span>
                      <span className="text-slate-300">{record.nucleotide_record.description}</span>
                    </div>
                    <div className="flex gap-6 font-mono text-[11px] text-slate-400 pt-2 border-t border-white/[0.06]">
                      <span>Length: {record.nucleotide_record.length} bp</span>
                      {record.nucleotide_record.gc_content && (
                        <span>GC: {record.nucleotide_record.gc_content.toFixed(1)}%</span>
                      )}
                      {record.nucleotide_record.molecular_weight_kda && (
                        <span>MW: {record.nucleotide_record.molecular_weight_kda.toFixed(2)} kDa</span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Card 2: UniProtKB / Swiss-Prot */}
              {record.protein_record && (
                <div className="border border-white/[0.08] bg-[#0e1314] p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <BookOpen size={15} className="text-[#f0c778]" />
                      <span className="font-mono text-xs font-semibold uppercase text-slate-200">
                        UniProtKB / Swiss-Prot Entry
                      </span>
                    </div>
                    <a
                      href={`https://www.uniprot.org/uniprotkb/${record.protein_record.accession}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 font-mono text-[10px] text-[#f0c778] hover:underline"
                    >
                      UniProt <ExternalLink size={10} />
                    </a>
                  </div>

                  <div className="space-y-3 text-xs">
                    <div>
                      <span className="font-mono text-slate-500">Protein Name: </span>
                      <span className="text-[#eee9de] font-medium">{record.protein_record.protein_name}</span>
                    </div>
                    <div className="flex gap-4 font-mono text-[11px] text-slate-400">
                      <span>Entry: {record.protein_record.entry_name}</span>
                      <span>Accession: {record.protein_record.accession}</span>
                      <span>Length: {record.protein_record.length} aa</span>
                    </div>

                    {/* Active Sites / PTMs / Disulfides */}
                    {(record.protein_record.active_sites.length > 0 ||
                      record.protein_record.ptms.length > 0 ||
                      record.protein_record.disulfide_bonds.length > 0) && (
                      <div className="pt-2 border-t border-white/[0.06] space-y-1">
                        <span className="font-mono text-[10px] uppercase text-slate-500 block">
                          Biochemical Features:
                        </span>
                        {record.protein_record.active_sites.map((site, i) => (
                          <div key={i} className="font-mono text-[11px] text-[#8cd1c7]">
                            • Active site: {String(site.description || "catalytic residue")} (pos {String(site.position ?? "")})
                          </div>
                        ))}
                        {record.protein_record.ptms.map((ptm, i) => (
                          <div key={i} className="font-mono text-[11px] text-[#f0c778]">
                            • PTM: {String(ptm.description || "modification")} (pos {String(ptm.position ?? "")})
                          </div>
                        ))}
                        {record.protein_record.disulfide_bonds.map((dsb, i) => (
                          <div key={i} className="font-mono text-[11px] text-[#70c4b5]">
                            • Disulfide bond: residues {String(dsb.start ?? "")} &harr; {String(dsb.end ?? "")}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* PIR Cross-References */}
                    {record.protein_record.pir_ids.length > 0 && (
                      <div className="pt-2 border-t border-white/[0.06]">
                        <span className="font-mono text-[10px] uppercase text-slate-500 block">
                          Legacy PIR Cross-Reference:
                        </span>
                        <div className="flex gap-2 mt-1">
                          {record.protein_record.pir_ids.map((id, i) => (
                            <span
                              key={i}
                              className="border border-white/10 bg-black/40 px-2 py-0.5 font-mono text-[10px] text-slate-300"
                            >
                              PIR:{id}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Card 3: Functional Domains & Motif Scanner (Pfam & PROSITE) */}
              <div className="border border-white/[0.08] bg-[#0e1314] p-5">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Layers size={15} className="text-[#8cd1c7]" />
                    <span className="font-mono text-xs font-semibold uppercase text-slate-200">
                      Functional Domains & Motifs (Pfam & PROSITE)
                    </span>
                  </div>
                </div>

                {/* Pre-identified domains */}
                {record.domains.length > 0 && (
                  <div className="space-y-2 mb-4">
                    <span className="font-mono text-[10px] uppercase text-slate-500 block">
                      Annotated Domains ({record.domains.length})
                    </span>
                    <div className="space-y-1.5">
                      {record.domains.map((dom, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between border border-white/[0.06] bg-black/30 p-2 font-mono text-xs"
                        >
                          <div>
                            <span className="text-[#d5a65b] font-semibold">{dom.id}</span>
                            <span className="text-slate-400 ml-2">{dom.name}</span>
                          </div>
                          <span className="text-[10px] text-slate-500">
                            {dom.database} · {dom.start}..{dom.end}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Interactive Motif Scanner */}
                <div className="pt-3 border-t border-white/[0.06] space-y-2">
                  <span className="font-mono text-[10px] uppercase text-slate-400 block">
                    Interactive PROSITE Motif Scanner
                  </span>
                  <div className="flex gap-2">
                    <input
                      value={scanInputSeq}
                      onChange={(e) => setScanInputSeq(e.target.value)}
                      placeholder="Paste peptide sequence to scan for PROSITE signatures..."
                      className="flex-1 border border-white/10 bg-black/40 px-3 py-1 font-mono text-xs text-slate-200 outline-none"
                    />
                    <button
                      onClick={handleMotifScan}
                      disabled={scanning}
                      className="border border-[#d5a65b]/50 bg-[#d5a65b]/10 px-3 py-1 font-mono text-xs text-[#f0c778] hover:bg-[#d5a65b]/20 disabled:opacity-50"
                    >
                      {scanning ? "Scanning..." : "Scan"}
                    </button>
                  </div>

                  {scanResults.length > 0 && (
                    <div className="space-y-1 mt-2">
                      {scanResults.map((m, idx) => (
                        <div
                          key={idx}
                          className="border border-[#70c4b5]/30 bg-[#70c4b5]/10 p-2 font-mono text-xs text-[#8cd1c7]"
                        >
                          <div className="flex justify-between text-[11px] font-semibold">
                            <span>
                              {m.motif_id}: {m.motif_name}
                            </span>
                            <span>
                              Coords: {m.start}..{m.end}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-400 break-all mt-1">
                            Match: "{m.matched_sequence}"
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Card 4: KEGG Pathways */}
              {record.pathways.length > 0 && (
                <div className="border border-white/[0.08] bg-[#0e1314] p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Compass size={15} className="text-[#f0a2a2]" />
                      <span className="font-mono text-xs font-semibold uppercase text-slate-200">
                        KEGG Biological Pathways
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {record.pathways.map((pw, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between border border-white/[0.06] bg-black/30 p-2.5 text-xs"
                      >
                        <div>
                          <span className="font-mono text-[#f0a2a2] font-semibold">{pw.pathway_id}</span>
                          <span className="text-slate-300 ml-2">{pw.name}</span>
                          {pw.description && (
                            <p className="text-[11px] text-slate-500 mt-0.5">{pw.description}</p>
                          )}
                        </div>
                        <a
                          href={pw.url || `https://www.genome.jp/kegg-bin/show_pathway?${pw.pathway_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-slate-500 hover:text-white"
                        >
                          <ExternalLink size={12} />
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Card 5: Genomic Locus (Ensembl & UCSC) */}
              {record.locus && (
                <div className="border border-white/[0.08] bg-[#0e1314] p-5">
                  <div className="mb-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <GitBranch size={15} className="text-[#8e77bb]" />
                      <span className="font-mono text-xs font-semibold uppercase text-slate-200">
                        Genomic Locus & Archaic Tracks
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="font-mono text-slate-300">
                      chr{record.locus.chromosome}:{record.locus.start}-{record.locus.end} ({record.locus.assembly})
                    </div>
                    <div className="flex flex-wrap gap-2 pt-2 border-t border-white/[0.06]">
                      {record.locus.ensembl_url && (
                        <a
                          href={record.locus.ensembl_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 border border-white/10 px-2.5 py-1 font-mono text-[10px] text-slate-300 hover:border-[#8e77bb] hover:text-[#c1a9ec]"
                        >
                          Ensembl Gene <ExternalLink size={10} />
                        </a>
                      )}
                      {record.locus.ucsc_url && (
                        <a
                          href={record.locus.ucsc_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 border border-white/10 px-2.5 py-1 font-mono text-[10px] text-slate-300 hover:border-[#8e77bb] hover:text-[#c1a9ec]"
                        >
                          UCSC Archaic Track (Altai/Denisova) <ExternalLink size={10} />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: 3D Structure Viewer, CATH/SCOP, STRING PPI */}
            <div className="space-y-6">
              {/* 3D Structure & Mutations Card */}
              {record.structure_record ? (
                <div className="space-y-4">
                  <MolecularViewer
                    pdbId={record.structure_record.pdb_id}
                    title={record.structure_record.title}
                    resolution={record.structure_record.resolution_angstrom}
                    mutations={mutations}
                  />

                  {/* Structural Folds Badges */}
                  <div className="border border-white/[0.08] bg-[#0e1314] p-4 text-xs space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-[10px] uppercase text-slate-500">
                        Structural Classification (PDBe SIFTS)
                      </span>
                      <span className="font-mono text-[10px] text-slate-400">
                        Method: {record.structure_record.method}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {record.structure_record.cath_codes.map((c, i) => (
                        <span
                          key={i}
                          className="border border-[#70c4b5]/40 bg-[#70c4b5]/10 px-2 py-0.5 font-mono text-[10px] text-[#8cd1c7]"
                        >
                          CATH: {c}
                        </span>
                      ))}
                      {record.structure_record.scop_folds.map((s, i) => (
                        <span
                          key={i}
                          className="border border-[#f0c778]/40 bg-[#f0c778]/10 px-2 py-0.5 font-mono text-[10px] text-[#f0c778]"
                        >
                          SCOP: {s}
                        </span>
                      ))}
                    </div>

                    {/* Mapped Paleogenomic Mutations */}
                    {mutations.length > 0 && (
                      <div className="pt-2 border-t border-white/[0.06] space-y-1">
                        <span className="font-mono text-[10px] uppercase text-[#f0a2a2] block">
                          Paleogenomic Mutation Residues ({mutations.length}):
                        </span>
                        <div className="space-y-1">
                          {mutations.map((m, i) => (
                            <div
                              key={i}
                              className="flex items-center justify-between border border-white/[0.06] bg-black/40 px-2 py-1 font-mono text-[11px]"
                            >
                              <span className="text-[#f0a2a2] font-semibold">
                                Chain {m.chain}: {m.ancestral}
                                {m.position}
                                {m.derived}
                              </span>
                              <span className="text-slate-400 text-[10px]">{m.functional_impact}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="border border-white/[0.08] bg-[#0e1314] p-8 text-center text-xs text-slate-500">
                  <Box size={24} className="mx-auto mb-2 text-slate-600" />
                  No direct 3D crystallographic structure associated with this accession.
                </div>
              )}

              {/* STRING Interaction Network Card */}
              {record.interactions.length > 0 && (
                <div className="border border-white/[0.08] bg-[#0e1314] p-5">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Network size={15} className="text-[#d5a65b]" />
                      <span className="font-mono text-xs font-semibold uppercase text-slate-200">
                        Protein-Protein Interactions (STRING DB)
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-slate-500">
                      {record.interactions.length} Interactors
                    </span>
                  </div>

                  <div className="mb-3 flex items-center justify-between font-mono text-[10px] text-slate-500">
                    <span>Min Combined Score: {(stringScoreMin / 1000).toFixed(3)}</span>
                    <input
                      type="range"
                      min={150}
                      max={900}
                      step={50}
                      value={stringScoreMin}
                      onChange={(e) => setStringScoreMin(Number(e.target.value))}
                      className="w-32 accent-[#d5a65b]"
                    />
                  </div>

                  <div className="space-y-2 max-h-[320px] overflow-auto">
                    {record.interactions
                      .filter((edge) => edge.score >= stringScoreMin / 1000)
                      .map((edge, i) => (
                        <div
                          key={i}
                          className="border border-white/[0.06] bg-black/30 p-2.5 font-mono text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-slate-200 font-semibold">
                              {edge.source} &harr; {edge.target}
                            </span>
                            <span className="text-[#d5a65b] font-semibold">{edge.score.toFixed(3)}</span>
                          </div>

                          {/* Evidence Channels */}
                          <div className="flex flex-wrap gap-1 text-[9px] text-slate-400">
                            {Object.entries(edge.evidence_channels || {}).map(([ch, sc]) => (
                              <span
                                key={ch}
                                className="border border-white/10 bg-black/40 px-1 py-0.5"
                              >
                                {ch}: {(sc as number).toFixed(2)}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
