import React, { useEffect, useRef, useState } from "react";
import { Box, ExternalLink, Eye, RotateCw, Sparkles, ZoomIn } from "lucide-react";
import { fetchStructureCoordinates } from "../lib/api";

declare global {
  interface Window {
    $3Dmol?: {
      createViewer: (
        element: HTMLElement,
        config: { backgroundColor: string }
      ) => {
        addModel: (data: string, format: string) => void;
        setStyle: (sel: Record<string, unknown>, style: Record<string, unknown>) => void;
        addStyle: (sel: Record<string, unknown>, style: Record<string, unknown>) => void;
        addLabel: (
          text: string,
          options: Record<string, unknown>
        ) => void;
        removeAllLabels: () => void;
        zoomTo: () => void;
        render: () => void;
        clear: () => void;
        spin: (axis: string, speed?: number) => void;
      };
    };
  }
}

interface MutationItem {
  position: number;
  ancestral: string;
  derived: string;
  chain: string;
  functional_impact?: string;
}

interface MolecularViewerProps {
  pdbId: string;
  title?: string;
  resolution?: number | null;
  mutations?: MutationItem[];
  className?: string;
}

export const MolecularViewer: React.FC<MolecularViewerProps> = ({
  pdbId,
  title,
  resolution,
  mutations = [],
  className = "",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerInstanceRef = useRef<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [styleMode, setStyleMode] = useState<"cartoon" | "stick" | "sphere" | "ribbon">("cartoon");
  const [spinning, setSpinning] = useState(false);
  const [highlightMutations, setHighlightMutations] = useState(true);

  // Load 3Dmol.js script if not present
  useEffect(() => {
    if (window.$3Dmol) return;

    const existingScript = document.getElementById("3dmol-script");
    if (!existingScript) {
      const script = document.createElement("script");
      script.id = "3dmol-script";
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js";
      script.async = true;
      document.head.appendChild(script);
    }
  }, []);

  // Fetch coordinates and render viewer
  useEffect(() => {
    let canceled = false;
    setLoading(true);
    setError(null);

    const initViewer = async () => {
      try {
        // Wait for 3Dmol script with timeout
        let attempts = 0;
        while (!window.$3Dmol && attempts < 25) {
          await new Promise((r) => setTimeout(r, 200));
          attempts++;
        }

        const pdbData = await fetchStructureCoordinates(pdbId);
        if (canceled || !containerRef.current) return;

        if (window.$3Dmol) {
          containerRef.current.innerHTML = "";
          const viewer = window.$3Dmol.createViewer(containerRef.current, {
            backgroundColor: "#080c0d",
          });
          viewerInstanceRef.current = viewer;

          viewer.addModel(pdbData, "pdb");
          applyStyles(viewer, styleMode, highlightMutations);
          viewer.zoomTo();
          viewer.render();
        }
        setLoading(false);
      } catch (err: any) {
        if (!canceled) {
          setError(err.message || "Failed to load coordinates");
          setLoading(false);
        }
      }
    };

    initViewer();

    return () => {
      canceled = true;
      if (viewerInstanceRef.current) {
        try {
          viewerInstanceRef.current.clear();
        } catch {
          // ignore cleanup errors
        }
      }
    };
  }, [pdbId]);

  const applyStyles = (
    viewer: any,
    mode: "cartoon" | "stick" | "sphere" | "ribbon",
    showMutations: boolean
  ) => {
    if (!viewer) return;
    try {
      viewer.removeAllLabels();

      const baseStyle: Record<string, unknown> = {};
      if (mode === "cartoon") baseStyle.cartoon = { color: "spectrum" };
      else if (mode === "stick") baseStyle.stick = { colorscheme: "amino" };
      else if (mode === "sphere") baseStyle.sphere = { color: "spectrum", radius: 0.8 };
      else if (mode === "ribbon") baseStyle.ribbon = { color: "spectrum" };

      viewer.setStyle({}, baseStyle);

      if (showMutations && mutations.length > 0) {
        mutations.forEach((m) => {
          viewer.addStyle(
            { resi: m.position },
            { stick: { color: "#e06c75", radius: 0.35 } }
          );
          viewer.addLabel(`${m.ancestral}${m.position}${m.derived}`, {
            resi: m.position,
            backgroundColor: "#c86868",
            fontColor: "#ffffff",
            fontSize: 11,
          });
        });
      }
      viewer.render();
    } catch (e) {
      console.warn("Style update error", e);
    }
  };

  const handleStyleChange = (mode: "cartoon" | "stick" | "sphere" | "ribbon") => {
    setStyleMode(mode);
    if (viewerInstanceRef.current) {
      applyStyles(viewerInstanceRef.current, mode, highlightMutations);
    }
  };

  const toggleMutations = () => {
    const next = !highlightMutations;
    setHighlightMutations(next);
    if (viewerInstanceRef.current) {
      applyStyles(viewerInstanceRef.current, styleMode, next);
    }
  };

  const toggleSpin = () => {
    const next = !spinning;
    setSpinning(next);
    if (viewerInstanceRef.current) {
      if (next) {
        viewerInstanceRef.current.spin("y", 1);
      } else {
        viewerInstanceRef.current.spin("y", 0);
      }
    }
  };

  const resetView = () => {
    if (viewerInstanceRef.current) {
      viewerInstanceRef.current.zoomTo();
      viewerInstanceRef.current.render();
    }
  };

  return (
    <div className={`relative flex flex-col border border-white/[0.08] bg-[#080c0d] ${className}`}>
      {/* Header toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] bg-black/40 px-3 py-2 text-xs">
        <div className="flex items-center gap-2">
          <Box size={14} className="text-[#d5a65b]" />
          <span className="font-mono font-semibold uppercase text-slate-200">{pdbId}</span>
          {resolution && (
            <span className="font-mono text-[10px] text-slate-400">
              {resolution.toFixed(2)} Å
            </span>
          )}
        </div>

        {/* View style controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleStyleChange("cartoon")}
            className={`px-2 py-0.5 font-mono text-[10px] transition ${
              styleMode === "cartoon"
                ? "border border-[#d5a65b]/60 bg-[#d5a65b]/20 text-[#f0c778]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Cartoon
          </button>
          <button
            onClick={() => handleStyleChange("stick")}
            className={`px-2 py-0.5 font-mono text-[10px] transition ${
              styleMode === "stick"
                ? "border border-[#d5a65b]/60 bg-[#d5a65b]/20 text-[#f0c778]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Stick
          </button>
          <button
            onClick={() => handleStyleChange("sphere")}
            className={`px-2 py-0.5 font-mono text-[10px] transition ${
              styleMode === "sphere"
                ? "border border-[#d5a65b]/60 bg-[#d5a65b]/20 text-[#f0c778]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Spheres
          </button>
          {mutations.length > 0 && (
            <button
              onClick={toggleMutations}
              className={`flex items-center gap-1 border px-2 py-0.5 font-mono text-[10px] transition ${
                highlightMutations
                  ? "border-[#c86868]/60 bg-[#c86868]/20 text-[#f0a2a2]"
                  : "border-white/10 text-slate-400 hover:text-slate-200"
              }`}
              title="Highlight paleogenomic mutations"
            >
              <Sparkles size={10} />
              Mutations ({mutations.length})
            </button>
          )}
          <button
            onClick={toggleSpin}
            className={`p-1 transition ${
              spinning ? "text-[#d5a65b]" : "text-slate-500 hover:text-slate-300"
            }`}
            title="Auto-rotate"
          >
            <RotateCw size={13} className={spinning ? "animate-spin" : ""} />
          </button>
          <button
            onClick={resetView}
            className="p-1 text-slate-500 transition hover:text-slate-300"
            title="Reset Zoom"
          >
            <ZoomIn size={13} />
          </button>
          <a
            href={`https://www.rcsb.org/3d-view/${pdbId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1 text-slate-500 transition hover:text-[#d5a65b]"
            title="Open in RCSB PDB 3D View"
          >
            <ExternalLink size={13} />
          </a>
        </div>
      </div>

      {/* WebGL Canvas Viewport */}
      <div className="relative h-[360px] w-full bg-[#080c0d]">
        <div ref={containerRef} className="h-full w-full" />

        {loading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#080c0d]/80 text-xs text-slate-400">
            <RotateCw size={18} className="animate-spin text-[#d5a65b]" />
            <span className="mt-2 font-mono text-[11px] tracking-wider text-slate-400">
              Loading 3D coordinates for {pdbId}...
            </span>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-[#080c0d]/90 text-xs">
            <Box size={24} className="mb-2 text-[#c86868]" />
            <div className="font-mono text-sm text-[#f0a2a2]">WebGL viewer unavailable</div>
            <p className="mt-1 max-w-sm text-slate-400">{error}</p>
            <a
              href={`https://www.rcsb.org/structure/${pdbId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 border border-[#d5a65b]/40 bg-[#d5a65b]/10 px-3 py-1 font-mono text-[10px] text-[#f0c778] hover:bg-[#d5a65b]/20"
            >
              View on RCSB PDB <ExternalLink size={12} />
            </a>
          </div>
        )}
      </div>

      {/* Footer metadata */}
      {title && (
        <div className="border-t border-white/[0.06] bg-black/30 px-3 py-1.5 text-[11px] text-slate-400">
          <span className="line-clamp-1 italic">{title}</span>
        </div>
      )}
    </div>
  );
};
