import React from "react";
import { motion } from "framer-motion";
import { ArrowRight, BookOpen, Dna, Info, Sparkles } from "lucide-react";

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

interface MinimalLandingViewProps {
  onNavigate: (view: ViewKey) => void;
}

export function MinimalLandingView({ onNavigate }: MinimalLandingViewProps) {
  return (
    <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-12 md:py-20">
      {/* AMBIENT ANIMATED BACKGROUND ELEMENTS */}
      <motion.div
        animate={{
          scale: [1, 1.2, 1],
          opacity: [0.15, 0.28, 0.15],
          rotate: [0, 45, 0],
        }}
        transition={{
          duration: 12,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="pointer-events-none absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full bg-gradient-to-tr from-[#d5a65b]/25 via-[#70c4b5]/15 to-transparent blur-3xl md:h-[650px] md:w-[650px]"
      />

      {/* SUBTLE BACKGROUND GRID STRATA */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.1),rgba(255,255,255,0))]" />

      {/* FLOATING SUBTLE PARTICLES (ANIMATED WITH MOTION) */}
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className="pointer-events-none absolute h-1 w-1 rounded-full bg-[#d5a65b]/30"
          style={{
            top: `${20 + i * 12}%`,
            left: `${15 + (i * 14) % 70}%`,
          }}
          animate={{
            y: [-10, 10, -10],
            opacity: [0.2, 0.6, 0.2],
          }}
          transition={{
            duration: 4 + i,
            repeat: Infinity,
            ease: "easeInOut",
            delay: i * 0.5,
          }}
        />
      ))}

      {/* CENTRAL MINIMAL CONTENT */}
      <div className="relative z-10 flex max-w-3xl flex-col items-center text-center space-y-8">
        {/* PILL BADGE */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="inline-flex items-center gap-2 border border-[#d5a65b]/35 bg-[#d5a65b]/10 px-3.5 py-1.5 text-xs text-[#f0c778]"
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#70c4b5] opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[#70c4b5]" />
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.22em]">
            PaleoDB // Prehistoric Molecular Genomics
          </span>
        </motion.div>

        {/* HEADLINE */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1, ease: "easeOut" }}
          className="space-y-3"
        >
          <h1 className="font-display text-4xl font-semibold tracking-tight text-[#eee9de] sm:text-5xl md:text-6xl md:leading-[1.15]">
            Deep-Time Genomics.{" "}
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-[#f0c778] via-[#d5a65b] to-[#70c4b5]">
              Unearthing Extinct Life.
            </span>
          </h1>
          <p className="mx-auto max-w-xl text-sm leading-relaxed text-slate-400 sm:text-base">
            An open paleogenomics workstation connecting ancient DNA sequences, pairwise extant synteny,
            3D protein structural adaptations, and grounded evolutionary literature.
          </p>
        </motion.div>

        {/* CALL TO ACTION BUTTONS */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
          className="flex flex-wrap items-center justify-center gap-3 pt-2"
        >
          <button
            onClick={() => onNavigate("atlas")}
            className="group flex items-center gap-2.5 border border-[#d5a65b] bg-[#d5a65b] px-6 py-3 font-mono text-xs uppercase tracking-[0.16em] text-[#0b0f10] font-semibold transition hover:bg-[#e4b568] hover:shadow-[0_0_25px_rgba(213,166,91,0.35)]"
          >
            <BookOpen size={15} />
            <span>Enter Taxa Atlas</span>
            <ArrowRight size={14} className="transition-transform group-hover:translate-x-1" />
          </button>

          <button
            onClick={() => onNavigate("workbench")}
            className="flex items-center gap-2 border border-white/15 bg-white/[0.04] px-5 py-3 font-mono text-xs uppercase tracking-[0.16em] text-slate-300 transition hover:border-[#70c4b5]/50 hover:bg-[#70c4b5]/10 hover:text-[#8cd1c7]"
          >
            <Dna size={15} />
            <span>Sequence Workbench</span>
          </button>

          <button
            onClick={() => onNavigate("about")}
            className="flex items-center gap-2 border border-white/10 bg-transparent px-4 py-3 font-mono text-xs uppercase tracking-[0.16em] text-slate-400 transition hover:border-white/20 hover:text-slate-200"
          >
            <Info size={14} />
            <span>About Project</span>
          </button>
        </motion.div>

        {/* SUBTLE TICKER / PILLS */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.35, ease: "easeOut" }}
          className="pt-8 flex flex-wrap items-center justify-center gap-2 text-[11px] text-slate-500 font-mono"
        >
          <span className="border border-white/[0.06] bg-black/20 px-3 py-1">18 Codified Prehistoric Taxa</span>
          <span className="text-slate-700 hidden sm:inline">/</span>
          <span className="border border-white/[0.06] bg-black/20 px-3 py-1">Pairwise Extant Synteny</span>
          <span className="text-slate-700 hidden sm:inline">/</span>
          <span className="border border-white/[0.06] bg-black/20 px-3 py-1">6 Federated Biological DBs</span>
          <span className="text-slate-700 hidden sm:inline">/</span>
          <span className="border border-white/[0.06] bg-black/20 px-3 py-1">Grounded Literature RAG</span>
        </motion.div>
      </div>
    </div>
  );
}
