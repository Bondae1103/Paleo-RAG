import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRightLeft,
  Check,
  CircleCheck,
  Copy,
  Dna,
  FileCode,
  FileText,
  Play,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import {
  convertSequence,
  SequenceFormat,
  translateDogma,
  TranslationResponse,
  validateSequence,
  validateSubmission,
  ValidationResult,
} from "../lib/api";

const PRESET_MAMMOTH =
  "ATGGTGCACCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAACGTGGATGAAGTTGGTGGTGAGGCCCTGGGCAGGCTGCTGGTCGTCTAC";
const PRESET_FOXP2 =
  "ATGCCATCACCTACTTTCTCCCCTACCCCATCTCTTCAGCCTCACCACCAACATCACCTCCCACCGCCTCTACACCACCAGCAGCACAGCTCCATCTCTCTCTCTCCGGCTGTGCACATCAGCACCTCTCATGGCTTCCCAGCTGCAGCAG";
const PRESET_PLA =
  "ATGAAAAGAAAAATTTTAGCTCTTTTAGTCACAGCAGCCATGAGTGTAAGTTTTACACAAGCAGTAAATGATGACGCTTATTTACGTACAACTGCAGCAGCAAGCACTGCCTATACTGCTACTGCACCAAGTATTGTTGCCGCACCAGTCGTAGTAGCAACAGTTGAA";

interface SequenceWorkbenchViewProps {
  initialSequence?: string;
  initialLocus?: string;
  initialOrganism?: string;
}

export const SequenceWorkbenchView: React.FC<SequenceWorkbenchViewProps> = ({
  initialSequence,
  initialLocus,
  initialOrganism,
}) => {
  const [activeTab, setActiveTab] = useState<"validate" | "convert" | "dogma" | "submission">("validate");

  // State: Validation
  const [valSeq, setValSeq] = useState(initialSequence || PRESET_MAMMOTH);
  const [valResult, setValResult] = useState<ValidationResult | null>(null);
  const [valLoading, setValLoading] = useState(false);

  // State: Conversion
  const [convInput, setConvInput] = useState(
    initialSequence
      ? `>${(initialOrganism || "Taxon").replace(/\s+/g, "_")}_${initialLocus || "GENE"}\n${initialSequence}`
      : `>Mammuthus_primigenius_HBB\n${PRESET_MAMMOTH}`
  );
  const [convInFormat, setConvInFormat] = useState<SequenceFormat>("fasta");
  const [convOutFormat, setConvOutFormat] = useState<SequenceFormat>("genbank");
  const [convOutput, setConvOutput] = useState("");
  const [convLoading, setConvLoading] = useState(false);

  // State: Central Dogma
  const [dogmaSeq, setDogmaSeq] = useState(initialSequence || PRESET_PLA);
  const [minOrfAa, setMinOrfAa] = useState(15);
  const [dogmaResult, setDogmaResult] = useState<TranslationResponse | null>(null);
  const [dogmaLoading, setDogmaLoading] = useState(false);
  const [activeFrameIndex, setActiveFrameIndex] = useState<number>(0);

  // State: Submission Validator
  const [subLocus, setSubLocus] = useState(initialLocus || "MAMPR_HBB");
  const [subOrganism, setSubOrganism] = useState(initialOrganism || "Mammuthus primigenius");
  const [subDefinition, setSubDefinition] = useState(
    `${initialOrganism || "Mammuthus primigenius"} ${initialLocus || "HBB"} gene, coding sequence.`
  );
  const [subAuthors, setSubAuthors] = useState("Campbell, K.L., Krause, J., Poinar, H.N.");
  const [subMolType, setSubMolType] = useState("DNA");
  const [subTopology, setSubTopology] = useState("linear");
  const [subDivision, setSubDivision] = useState("MAM");
  const [subSeq, setSubSeq] = useState(initialSequence || PRESET_MAMMOTH);
  const [subResult, setSubResult] = useState<{
    is_valid: boolean;
    errors: string[];
    warnings: string[];
    preview?: string | null;
  } | null>(null);
  const [subLoading, setSubLoading] = useState(false);

  // Handlers
  const handleValidate = async () => {
    if (!valSeq.trim()) return;
    setValLoading(true);
    try {
      const res = await validateSequence(valSeq.trim());
      setValResult(res);
      toast.success("Sequence analyzed successfully");
    } catch (err: any) {
      toast.error(`Validation error: ${err.message}`);
    } finally {
      setValLoading(false);
    }
  };

  const handleConvert = async () => {
    if (!convInput.trim()) return;
    setConvLoading(true);
    try {
      const res = await convertSequence(convInput, convInFormat, convOutFormat);
      setConvOutput(res.output_text);
      toast.success(`Converted ${res.record_count} sequence record(s) to ${convOutFormat.toUpperCase()}`);
    } catch (err: any) {
      toast.error(`Conversion error: ${err.message}`);
    } finally {
      setConvLoading(false);
    }
  };

  const handleDogma = async () => {
    if (!dogmaSeq.trim()) return;
    setDogmaLoading(true);
    try {
      const res = await translateDogma(dogmaSeq.trim(), minOrfAa);
      setDogmaResult(res);
      toast.success("Translation and 6-frame ORF detection complete");
    } catch (err: any) {
      toast.error(`Dogma engine error: ${err.message}`);
    } finally {
      setDogmaLoading(false);
    }
  };

  const handleSubmissionCheck = async () => {
    if (!subSeq.trim()) return;
    setSubLoading(true);
    try {
      const authorsList = subAuthors
        .split(",")
        .map((a) => a.trim())
        .filter(Boolean);
      const res = await validateSubmission({
        locus_name: subLocus,
        sequence: subSeq.trim(),
        organism: subOrganism,
        definition: subDefinition,
        authors: authorsList,
        molecule_type: subMolType,
        topology: subTopology,
        division: subDivision,
      });
      setSubResult({
        is_valid: res.is_valid,
        errors: res.errors,
        warnings: res.warnings,
        preview: res.preview_genbank_record,
      });
      if (res.is_valid) {
        toast.success("Submission checklist verified compliant with INSDC standards");
      } else {
        toast.error("Submission errors detected - review checklist");
      }
    } catch (err: any) {
      toast.error(`Submission validator error: ${err.message}`);
    } finally {
      setSubLoading(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`Copied ${label} to clipboard`);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-auto bg-[#0b0f10] p-4 md:p-8">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.24em] text-[#79bcb3]">
            <span className="h-px w-5 bg-[#79bcb3]" />
            Module 1 · Sequence Submission & Analysis (CO1)
          </div>
          <h1 className="font-display text-2xl font-semibold tracking-[-0.03em] text-[#eee9de] md:text-3xl">
            Sequence Workbench
          </h1>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-400">
            IUPAC biochemical sequence validation, bidirectional Biopython format conversion, Central Dogma 6-frame
            ORF translation, and INSDC GenBank/EMBL submission compliance engine.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap items-center gap-1 border border-white/10 bg-white/[0.02] p-1 font-mono text-xs">
          <button
            onClick={() => setActiveTab("validate")}
            className={`flex items-center gap-1.5 px-3 py-1.5 transition ${
              activeTab === "validate"
                ? "bg-[#d5a65b]/20 font-semibold text-[#f0c778]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Dna size={13} />
            IUPAC Validator
          </button>
          <button
            onClick={() => setActiveTab("convert")}
            className={`flex items-center gap-1.5 px-3 py-1.5 transition ${
              activeTab === "convert"
                ? "bg-[#d5a65b]/20 font-semibold text-[#f0c778]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ArrowRightLeft size={13} />
            Format Converter
          </button>
          <button
            onClick={() => setActiveTab("dogma")}
            className={`flex items-center gap-1.5 px-3 py-1.5 transition ${
              activeTab === "dogma"
                ? "bg-[#d5a65b]/20 font-semibold text-[#f0c778]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Sparkles size={13} />
            Central Dogma & ORFs
          </button>
          <button
            onClick={() => setActiveTab("submission")}
            className={`flex items-center gap-1.5 px-3 py-1.5 transition ${
              activeTab === "submission"
                ? "bg-[#d5a65b]/20 font-semibold text-[#f0c778]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileCode size={13} />
            Submission Validator
          </button>
        </div>
      </div>

      {/* Tab 1: IUPAC Validator */}
      {activeTab === "validate" && (
        <div className="space-y-6">
          <div className="border border-white/[0.08] bg-[#0e1314] p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs font-semibold uppercase text-slate-300">
                Input Molecular Sequence (DNA, RNA, or Protein)
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500">Presets:</span>
                <button
                  onClick={() => setValSeq(PRESET_MAMMOTH)}
                  className="border border-white/10 px-2 py-0.5 font-mono text-[10px] text-slate-400 hover:border-[#d5a65b]/40 hover:text-[#f0c778]"
                >
                  Mammoth HBB
                </button>
                <button
                  onClick={() => setValSeq(PRESET_FOXP2)}
                  className="border border-white/10 px-2 py-0.5 font-mono text-[10px] text-slate-400 hover:border-[#d5a65b]/40 hover:text-[#f0c778]"
                >
                  Neanderthal FOXP2
                </button>
                <button
                  onClick={() => setValSeq(PRESET_PLA)}
                  className="border border-white/10 px-2 py-0.5 font-mono text-[10px] text-slate-400 hover:border-[#d5a65b]/40 hover:text-[#f0c778]"
                >
                  Y. pestis Pla
                </button>
              </div>
            </div>

            <textarea
              rows={4}
              value={valSeq}
              onChange={(e) => setValSeq(e.target.value)}
              className="w-full font-mono text-xs leading-relaxed border border-white/10 bg-black/40 p-3 text-slate-200 outline-none focus:border-[#4f9f96]/60"
              placeholder="Paste raw sequence or IUPAC string..."
            />

            <div className="mt-3 flex justify-end">
              <button
                onClick={handleValidate}
                disabled={valLoading}
                className="flex items-center gap-1.5 bg-[#d5a65b] px-4 py-2 font-mono text-xs font-semibold uppercase tracking-wider text-[#17130d] transition hover:bg-[#f0c778] disabled:opacity-50"
              >
                <Play size={13} />
                {valLoading ? "Analyzing..." : "Validate Sequence"}
              </button>
            </div>
          </div>

          {/* Validation Results Metrics */}
          {valResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                <div className="border border-white/[0.08] bg-[#0e1314] p-4 text-center">
                  <span className="block font-mono text-[10px] uppercase text-slate-500">Classification</span>
                  <span className="font-display text-lg font-semibold uppercase text-[#70c4b5]">
                    {valResult.seq_type}
                  </span>
                </div>
                <div className="border border-white/[0.08] bg-[#0e1314] p-4 text-center">
                  <span className="block font-mono text-[10px] uppercase text-slate-500">Sequence Length</span>
                  <span className="font-display text-lg font-semibold text-[#eee9de]">
                    {valResult.length} {valResult.seq_type === "protein" ? "aa" : "bp"}
                  </span>
                </div>
                <div className="border border-white/[0.08] bg-[#0e1314] p-4 text-center">
                  <span className="block font-mono text-[10px] uppercase text-slate-500">GC Content</span>
                  <span className="font-display text-lg font-semibold text-[#f0c778]">
                    {valResult.gc_percent.toFixed(1)}%
                  </span>
                </div>
                <div className="border border-white/[0.08] bg-[#0e1314] p-4 text-center">
                  <span className="block font-mono text-[10px] uppercase text-slate-500">Molecular Weight</span>
                  <span className="font-display text-lg font-semibold text-[#8cd1c7]">
                    {valResult.molecular_weight_kda.toFixed(2)} kDa
                  </span>
                </div>
                <div className="border border-white/[0.08] bg-[#0e1314] p-4 text-center">
                  <span className="block font-mono text-[10px] uppercase text-slate-500">Ambiguity Index</span>
                  <span className="font-display text-lg font-semibold text-[#eee9de]">
                    {(valResult.ambiguity_index * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              <div
                className={`flex items-start gap-3 border p-4 ${
                  valResult.is_valid
                    ? "border-[#4f9f96]/30 bg-[#4f9f96]/[0.06]"
                    : "border-[#c86868]/40 bg-[#c86868]/[0.08]"
                }`}
              >
                {valResult.is_valid ? (
                  <CircleCheck size={18} className="text-[#70c4b5] mt-0.5" />
                ) : (
                  <AlertTriangle size={18} className="text-[#f0a2a2] mt-0.5" />
                )}
                <div>
                  <div className="font-mono text-xs font-semibold uppercase text-slate-200">
                    {valResult.is_valid ? "Valid IUPAC Sequence" : "Invalid Sequence Characters Detected"}
                  </div>
                  <div className="mt-1 text-xs text-slate-400">{valResult.details}</div>
                  {valResult.invalid_characters.length > 0 && (
                    <div className="mt-2 flex gap-1">
                      {valResult.invalid_characters.map((ch, idx) => (
                        <span
                          key={idx}
                          className="border border-[#c86868] bg-[#c86868]/20 px-1.5 py-0.5 font-mono text-[10px] text-[#f0a2a2]"
                        >
                          '{ch}'
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Format Converter */}
      {activeTab === "convert" && (
        <div className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Input Column */}
            <div className="flex flex-col border border-white/[0.08] bg-[#0e1314] p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase text-slate-300">Input Sequence</span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500">Format:</span>
                  <select
                    value={convInFormat}
                    onChange={(e) => setConvInFormat(e.target.value as SequenceFormat)}
                    className="border border-white/10 bg-black/40 px-2 py-1 font-mono text-xs text-slate-200 outline-none"
                  >
                    <option value="fasta">FASTA</option>
                    <option value="genbank">GenBank</option>
                    <option value="embl">EMBL</option>
                  </select>
                </div>
              </div>

              <textarea
                rows={12}
                value={convInput}
                onChange={(e) => setConvInput(e.target.value)}
                className="flex-1 w-full font-mono text-xs leading-relaxed border border-white/10 bg-black/40 p-3 text-slate-200 outline-none focus:border-[#4f9f96]/60"
                placeholder="Paste FASTA, GenBank, or EMBL text..."
              />

              <div className="mt-4 flex justify-between items-center">
                <button
                  onClick={() =>
                    setConvInput(`>HQ184444.1 Mammuthus primigenius hemoglobin subunit beta (HBB) gene\n${PRESET_MAMMOTH}`)
                  }
                  className="font-mono text-[10px] text-slate-500 hover:text-[#d5a65b]"
                >
                  Load Mammoth HBB FASTA
                </button>
                <button
                  onClick={handleConvert}
                  disabled={convLoading}
                  className="flex items-center gap-1.5 bg-[#d5a65b] px-4 py-2 font-mono text-xs font-semibold uppercase tracking-wider text-[#17130d] transition hover:bg-[#f0c778] disabled:opacity-50"
                >
                  <ArrowRightLeft size={13} />
                  {convLoading ? "Converting..." : "Convert Format"}
                </button>
              </div>
            </div>

            {/* Output Column */}
            <div className="flex flex-col border border-white/[0.08] bg-[#0e1314] p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase text-slate-300">Converted Output</span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500">Target:</span>
                  <select
                    value={convOutFormat}
                    onChange={(e) => setConvOutFormat(e.target.value as SequenceFormat)}
                    className="border border-white/10 bg-black/40 px-2 py-1 font-mono text-xs text-slate-200 outline-none"
                  >
                    <option value="genbank">GenBank</option>
                    <option value="embl">EMBL</option>
                    <option value="fasta">FASTA</option>
                  </select>
                </div>
              </div>

              <textarea
                readOnly
                rows={12}
                value={convOutput}
                className="flex-1 w-full font-mono text-xs leading-relaxed border border-white/10 bg-black/60 p-3 text-[#8cd1c7] outline-none"
                placeholder="Converted sequence will appear here..."
              />

              <div className="mt-4 flex justify-end">
                {convOutput && (
                  <button
                    onClick={() => copyToClipboard(convOutput, "Converted Output")}
                    className="flex items-center gap-1.5 border border-white/10 bg-white/[0.04] px-3 py-1.5 font-mono text-xs text-slate-300 hover:bg-white/[0.08]"
                  >
                    <Copy size={13} />
                    Copy Converted Record
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Central Dogma & 6-Frame ORFs */}
      {activeTab === "dogma" && (
        <div className="space-y-6">
          <div className="border border-white/[0.08] bg-[#0e1314] p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs font-semibold uppercase text-slate-300">
                Input Coding DNA Strand (5' &rarr; 3')
              </span>
              <div className="flex items-center gap-3">
                <span className="font-mono text-[10px] text-slate-500">Min ORF Length:</span>
                <input
                  type="number"
                  min={5}
                  max={200}
                  value={minOrfAa}
                  onChange={(e) => setMinOrfAa(Number(e.target.value))}
                  className="w-16 border border-white/10 bg-black/40 px-2 py-1 font-mono text-xs text-slate-200 outline-none"
                />
                <span className="font-mono text-[10px] text-slate-500">aa</span>
              </div>
            </div>

            <textarea
              rows={4}
              value={dogmaSeq}
              onChange={(e) => setDogmaSeq(e.target.value)}
              className="w-full font-mono text-xs leading-relaxed border border-white/10 bg-black/40 p-3 text-slate-200 outline-none focus:border-[#4f9f96]/60"
              placeholder="Enter nucleotide sequence..."
            />

            <div className="mt-3 flex justify-end">
              <button
                onClick={handleDogma}
                disabled={dogmaLoading}
                className="flex items-center gap-1.5 bg-[#d5a65b] px-4 py-2 font-mono text-xs font-semibold uppercase tracking-wider text-[#17130d] transition hover:bg-[#f0c778] disabled:opacity-50"
              >
                <Sparkles size={13} />
                {dogmaLoading ? "Translating..." : "Execute Dogma Translation"}
              </button>
            </div>
          </div>

          {dogmaResult && (
            <div className="space-y-6">
              {/* RNA and Reverse Complement */}
              <div className="grid gap-4 md:grid-cols-2">
                <div className="border border-white/[0.08] bg-[#0e1314] p-4">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase text-[#70c4b5]">
                      Transcribed mRNA (5' &rarr; 3')
                    </span>
                    <button
                      onClick={() => copyToClipboard(dogmaResult.rna_sequence, "mRNA")}
                      className="text-slate-500 hover:text-slate-300"
                    >
                      <Copy size={12} />
                    </button>
                  </div>
                  <div className="font-mono text-xs break-all text-slate-300">{dogmaResult.rna_sequence}</div>
                </div>

                <div className="border border-white/[0.08] bg-[#0e1314] p-4">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase text-[#d5a65b]">
                      Reverse Complement (5' &rarr; 3')
                    </span>
                    <button
                      onClick={() => copyToClipboard(dogmaResult.reverse_complement, "Reverse Complement")}
                      className="text-slate-500 hover:text-slate-300"
                    >
                      <Copy size={12} />
                    </button>
                  </div>
                  <div className="font-mono text-xs break-all text-slate-300">
                    {dogmaResult.reverse_complement}
                  </div>
                </div>
              </div>

              {/* Longest ORF Highlight */}
              {dogmaResult.longest_orf && (
                <div className="border border-[#d5a65b]/40 bg-[#d5a65b]/[0.08] p-5">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold uppercase text-[#f0c778]">
                      Candidate Coding ORF (Longest CDS)
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">
                      Frame {dogmaResult.longest_orf.frame > 0 ? `+${dogmaResult.longest_orf.frame}` : dogmaResult.longest_orf.frame} ·{" "}
                      Coords: {dogmaResult.longest_orf.start}..{dogmaResult.longest_orf.end} ({dogmaResult.longest_orf.length_nt} nt /{" "}
                      {dogmaResult.longest_orf.length_aa} aa)
                    </span>
                  </div>
                  <div className="font-mono text-xs break-all text-[#eee9de] p-3 bg-black/40 border border-white/10">
                    {dogmaResult.longest_orf.protein_sequence}
                  </div>
                </div>
              )}

              {/* 6-Frame Translation Tabs */}
              <div className="border border-white/[0.08] bg-[#0e1314] p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <span className="font-mono text-xs font-semibold uppercase text-slate-300">
                    6-Frame Translation Viewer
                  </span>
                  <div className="flex gap-1">
                    {dogmaResult.frames.map((f, idx) => (
                      <button
                        key={idx}
                        onClick={() => setActiveFrameIndex(idx)}
                        className={`px-3 py-1 font-mono text-xs transition ${
                          activeFrameIndex === idx
                            ? "bg-[#4f9f96]/30 border border-[#4f9f96] text-[#8cd1c7] font-semibold"
                            : "border border-white/10 text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Frame {f.frame > 0 ? `+${f.frame}` : f.frame}
                        {f.orfs.length > 0 && ` (${f.orfs.length})`}
                      </button>
                    ))}
                  </div>
                </div>

                {dogmaResult.frames[activeFrameIndex] && (
                  <div className="space-y-4">
                    <div className="border border-white/10 bg-black/40 p-4">
                      <div className="mb-2 font-mono text-[10px] uppercase text-slate-500">
                        Full Amino Acid Translation (Frame{" "}
                        {dogmaResult.frames[activeFrameIndex].frame > 0
                          ? `+${dogmaResult.frames[activeFrameIndex].frame}`
                          : dogmaResult.frames[activeFrameIndex].frame}
                        )
                      </div>
                      <div className="font-mono text-xs break-all text-slate-300 leading-relaxed">
                        {dogmaResult.frames[activeFrameIndex].translation}
                      </div>
                    </div>

                    {/* Detected ORFs in this frame */}
                    <div>
                      <div className="mb-2 font-mono text-xs uppercase text-slate-400">
                        ORFs Detected in Frame ({dogmaResult.frames[activeFrameIndex].orfs.length})
                      </div>
                      {dogmaResult.frames[activeFrameIndex].orfs.length === 0 ? (
                        <div className="border border-dashed border-white/10 p-4 text-center font-mono text-xs text-slate-600">
                          No ORFs meeting minimum length (&ge; {minOrfAa} aa) found in this frame.
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {dogmaResult.frames[activeFrameIndex].orfs.map((orf, oIdx) => (
                            <div
                              key={oIdx}
                              className="border border-white/[0.06] bg-black/20 p-3 font-mono text-xs"
                            >
                              <div className="flex items-center justify-between text-slate-400 mb-1 text-[11px]">
                                <span>
                                  ORF #{oIdx + 1} · {orf.start}..{orf.end} ({orf.length_nt} nt / {orf.length_aa} aa)
                                </span>
                                <button
                                  onClick={() => copyToClipboard(orf.protein_sequence, `ORF #${oIdx + 1}`)}
                                  className="text-slate-500 hover:text-slate-300"
                                >
                                  <Copy size={11} />
                                </button>
                              </div>
                              <div className="break-all text-[#8cd1c7]">{orf.protein_sequence}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: INSDC Submission Validator */}
      {activeTab === "submission" && (
        <div className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="border border-white/[0.08] bg-[#0e1314] p-5 space-y-4">
              <span className="font-mono text-xs font-semibold uppercase text-slate-300">
                INSDC Submission Metadata
              </span>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-mono text-[10px] uppercase text-slate-500 mb-1">
                    Locus Name
                  </label>
                  <input
                    value={subLocus}
                    onChange={(e) => setSubLocus(e.target.value)}
                    className="w-full border border-white/10 bg-black/40 px-3 py-1.5 font-mono text-xs text-slate-200 outline-none"
                    placeholder="MAMP_HBB"
                  />
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase text-slate-500 mb-1">
                    Organism (Scientific)
                  </label>
                  <input
                    value={subOrganism}
                    onChange={(e) => setSubOrganism(e.target.value)}
                    className="w-full border border-white/10 bg-black/40 px-3 py-1.5 font-mono text-xs text-slate-200 outline-none"
                    placeholder="Mammuthus primigenius"
                  />
                </div>
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-slate-500 mb-1">
                  Definition Line
                </label>
                <input
                  value={subDefinition}
                  onChange={(e) => setSubDefinition(e.target.value)}
                  className="w-full border border-white/10 bg-black/40 px-3 py-1.5 font-mono text-xs text-slate-200 outline-none"
                  placeholder="Organism gene, complete cds"
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-slate-500 mb-1">
                  Authors
                </label>
                <input
                  value={subAuthors}
                  onChange={(e) => setSubAuthors(e.target.value)}
                  className="w-full border border-white/10 bg-black/40 px-3 py-1.5 font-mono text-xs text-slate-200 outline-none"
                  placeholder="Author, A.B., Coauthor, C.D."
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-mono text-[10px] uppercase text-slate-500 mb-1">
                    Mol Type
                  </label>
                  <select
                    value={subMolType}
                    onChange={(e) => setSubMolType(e.target.value)}
                    className="w-full border border-white/10 bg-black/40 px-2 py-1.5 font-mono text-xs text-slate-200 outline-none"
                  >
                    <option value="DNA">DNA</option>
                    <option value="RNA">RNA</option>
                    <option value="mRNA">mRNA</option>
                  </select>
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase text-slate-500 mb-1">
                    Topology
                  </label>
                  <select
                    value={subTopology}
                    onChange={(e) => setSubTopology(e.target.value)}
                    className="w-full border border-white/10 bg-black/40 px-2 py-1.5 font-mono text-xs text-slate-200 outline-none"
                  >
                    <option value="linear">linear</option>
                    <option value="circular">circular</option>
                  </select>
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase text-slate-500 mb-1">
                    Division
                  </label>
                  <select
                    value={subDivision}
                    onChange={(e) => setSubDivision(e.target.value)}
                    className="w-full border border-white/10 bg-black/40 px-2 py-1.5 font-mono text-xs text-slate-200 outline-none"
                  >
                    <option value="MAM">MAM (Mammals)</option>
                    <option value="PRI">PRI (Primates)</option>
                    <option value="INV">INV (Invertebrates)</option>
                    <option value="BCT">BCT (Bacteria)</option>
                    <option value="VRL">VRL (Viruses)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase text-slate-500 mb-1">
                  Sequence Data
                </label>
                <textarea
                  rows={4}
                  value={subSeq}
                  onChange={(e) => setSubSeq(e.target.value)}
                  className="w-full font-mono text-xs leading-relaxed border border-white/10 bg-black/40 p-2.5 text-slate-200 outline-none"
                  placeholder="Paste nucleotide sequence..."
                />
              </div>

              <div className="flex justify-end">
                <button
                  onClick={handleSubmissionCheck}
                  disabled={subLoading}
                  className="flex items-center gap-1.5 bg-[#d5a65b] px-4 py-2 font-mono text-xs font-semibold uppercase tracking-wider text-[#17130d] transition hover:bg-[#f0c778] disabled:opacity-50"
                >
                  <CircleCheck size={13} />
                  {subLoading ? "Validating..." : "Validate INSDC Submission"}
                </button>
              </div>
            </div>

            {/* Checklist & Preview */}
            <div className="space-y-4">
              {subResult ? (
                <>
                  <div
                    className={`border p-4 ${
                      subResult.is_valid
                        ? "border-[#4f9f96]/40 bg-[#4f9f96]/[0.08]"
                        : "border-[#c86868]/40 bg-[#c86868]/[0.08]"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      {subResult.is_valid ? (
                        <CircleCheck size={18} className="text-[#70c4b5]" />
                      ) : (
                        <AlertTriangle size={18} className="text-[#f0a2a2]" />
                      )}
                      <span className="font-mono text-xs font-semibold uppercase text-slate-200">
                        {subResult.is_valid
                          ? "Submission Compliant with INSDC Standards"
                          : "Validation Errors Found"}
                      </span>
                    </div>

                    {subResult.errors.length > 0 && (
                      <div className="mt-2 space-y-1">
                        <span className="font-mono text-[10px] uppercase text-[#f0a2a2] block">Errors:</span>
                        {subResult.errors.map((err, i) => (
                          <div key={i} className="text-xs text-[#f0a2a2] flex items-center gap-1.5">
                            <span className="h-1 w-1 bg-[#c86868] rounded-full" />
                            {err}
                          </div>
                        ))}
                      </div>
                    )}

                    {subResult.warnings.length > 0 && (
                      <div className="mt-3 space-y-1">
                        <span className="font-mono text-[10px] uppercase text-[#f0c778] block">Warnings:</span>
                        {subResult.warnings.map((warn, i) => (
                          <div key={i} className="text-xs text-[#f0c778] flex items-center gap-1.5">
                            <span className="h-1 w-1 bg-[#d5a65b] rounded-full" />
                            {warn}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {subResult.preview && (
                    <div className="border border-white/[0.08] bg-[#0e1314] p-4">
                      <div className="mb-2 flex items-center justify-between">
                        <span className="font-mono text-xs font-semibold uppercase text-slate-300">
                          GenBank Flatfile Preview
                        </span>
                        <button
                          onClick={() => copyToClipboard(subResult.preview || "", "GenBank Flatfile")}
                          className="flex items-center gap-1 border border-white/10 px-2 py-0.5 font-mono text-[10px] text-slate-400 hover:text-slate-200"
                        >
                          <Copy size={11} />
                          Copy Flatfile
                        </button>
                      </div>
                      <pre className="max-h-[300px] overflow-auto font-mono text-[11px] text-[#8cd1c7] bg-black/60 p-3 border border-white/10">
                        {subResult.preview}
                      </pre>
                    </div>
                  )}
                </>
              ) : (
                <div className="border border-dashed border-white/10 p-8 text-center text-xs text-slate-600">
                  Fill in metadata and sequence on the left, then click Validate to generate the INSDC compliance report
                  and GenBank flatfile preview.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
