import React from "react";
import { BookOpen, Box, Compass, Database, Dna, ExternalLink, GitBranch, Layers, Network } from "lucide-react";
import { BioLookupResponse } from "../lib/api";

interface BioEntityCardProps {
  data: BioLookupResponse;
  onExploreMore?: (query: string) => void;
}

export const BioEntityCard: React.FC<BioEntityCardProps> = ({ data, onExploreMore }) => {
  return (
    <div className="space-y-4 border border-[#d5a65b]/40 bg-[#0d1213] p-4 text-xs font-sans">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <Database size={15} className="text-[#d5a65b]" />
          <div>
            <div className="font-mono text-xs font-semibold text-[#eee9de]">
              {data.query.toUpperCase()}
            </div>
            {data.organism && (
              <div className="font-mono text-[10px] italic text-slate-400">{data.organism}</div>
            )}
          </div>
        </div>
        <span className="border border-[#d5a65b]/40 bg-[#d5a65b]/10 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-[#f0c778]">
          Entity-Grounded
        </span>
      </div>

      {/* Nucleotide Accession */}
      {data.nucleotide_record && (
        <div className="border border-white/[0.06] bg-black/30 p-2.5">
          <div className="flex items-center justify-between mb-1">
            <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase text-[#70c4b5]">
              <Dna size={12} /> INSDC Nucleotide
            </span>
            <a
              href={`https://www.ncbi.nlm.nih.gov/nuccore/${data.nucleotide_record.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-500 hover:text-white"
            >
              <ExternalLink size={11} />
            </a>
          </div>
          <div className="font-mono text-xs text-slate-200">{data.nucleotide_record.id}</div>
          <p className="line-clamp-2 text-[11px] text-slate-400 mt-0.5">
            {data.nucleotide_record.description}
          </p>
        </div>
      )}

      {/* Protein UniProt Accession */}
      {data.protein_record && (
        <div className="border border-white/[0.06] bg-black/30 p-2.5">
          <div className="flex items-center justify-between mb-1">
            <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase text-[#f0c778]">
              <BookOpen size={12} /> UniProtKB / Swiss-Prot
            </span>
            <a
              href={`https://www.uniprot.org/uniprotkb/${data.protein_record.accession}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-500 hover:text-white"
            >
              <ExternalLink size={11} />
            </a>
          </div>
          <div className="font-mono text-xs text-slate-200">
            {data.protein_record.accession} ({data.protein_record.entry_name})
          </div>
          <p className="line-clamp-1 text-[11px] text-slate-400 mt-0.5">
            {data.protein_record.protein_name} · {data.protein_record.length} aa
          </p>
        </div>
      )}

      {/* 3D Structure */}
      {data.structure_record && (
        <div className="border border-white/[0.06] bg-black/30 p-2.5">
          <div className="flex items-center justify-between mb-1">
            <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase text-[#8cd1c7]">
              <Box size={12} /> RCSB PDB Structure
            </span>
            <a
              href={`https://www.rcsb.org/structure/${data.structure_record.pdb_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-500 hover:text-white"
            >
              <ExternalLink size={11} />
            </a>
          </div>
          <div className="font-mono text-xs text-slate-200">
            PDB ID: {data.structure_record.pdb_id}
            {data.structure_record.resolution_angstrom && (
              <span className="text-slate-400 font-normal ml-2">
                ({data.structure_record.resolution_angstrom.toFixed(2)} Å)
              </span>
            )}
          </div>
          {data.structure_record.cath_codes.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1 font-mono text-[9px] text-slate-400">
              <span>CATH: {data.structure_record.cath_codes[0]}</span>
              {data.structure_record.scop_folds.length > 0 && (
                <span>· SCOP: {data.structure_record.scop_folds[0]}</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Domains & Motifs */}
      {data.domains.length > 0 && (
        <div className="border border-white/[0.06] bg-black/30 p-2.5">
          <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase text-slate-400 mb-1.5">
            <Layers size={12} /> Pfam & PROSITE Domains
          </span>
          <div className="flex flex-wrap gap-1 font-mono text-[10px]">
            {data.domains.map((dom, i) => (
              <span
                key={i}
                className="border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-slate-300"
              >
                {dom.id} ({dom.name})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Pathways & Interactions summary */}
      <div className="grid grid-cols-2 gap-2 font-mono text-[10px]">
        {data.pathways.length > 0 && (
          <div className="border border-white/[0.06] bg-black/30 p-2 text-slate-300">
            <div className="text-slate-500 uppercase flex items-center gap-1 mb-0.5">
              <Compass size={11} /> KEGG Pathways
            </div>
            <div className="text-[#f0a2a2] font-semibold">{data.pathways[0].pathway_id}</div>
            <div className="line-clamp-1 text-[9px] text-slate-400">{data.pathways[0].name}</div>
          </div>
        )}

        {data.interactions.length > 0 && (
          <div className="border border-white/[0.06] bg-black/30 p-2 text-slate-300">
            <div className="text-slate-500 uppercase flex items-center gap-1 mb-0.5">
              <Network size={11} /> STRING PPI
            </div>
            <div className="text-[#d5a65b] font-semibold">{data.interactions.length} Interactors</div>
            <div className="text-[9px] text-slate-400">High-confidence network</div>
          </div>
        )}
      </div>

      {/* Genomic Locus */}
      {data.locus && (
        <div className="border border-white/[0.06] bg-black/30 p-2 font-mono text-[10px]">
          <div className="text-slate-500 uppercase flex items-center gap-1 mb-0.5">
            <GitBranch size={11} /> Ensembl / UCSC Locus
          </div>
          <div className="text-[#c1a9ec]">
            chr{data.locus.chromosome}:{data.locus.start}-{data.locus.end} ({data.locus.assembly})
          </div>
        </div>
      )}
    </div>
  );
};
