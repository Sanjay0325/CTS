"use client";

import { useEffect, useRef, useState } from "react";

interface MermaidDiagramProps {
  code: string;
  className?: string;
}

/** Renders Mermaid flowchart code as SVG. Uses client-side mermaid for rendering. */
export function MermaidDiagram({ code, className = "" }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code?.trim()) return;
    let cancelled = false;
    const id = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    const run = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "loose",
        });
        const { svg: result } = await mermaid.render(id, code);
        if (!cancelled) {
          setSvg(result);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(String(e));
          setSvg(null);
        }
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [code]);

  if (error) {
    return (
      <div className={`text-amber-500 text-xs p-2 ${className}`}>
        Mermaid render failed: {error}
      </div>
    );
  }
  if (svg) {
    return (
      <div
        ref={containerRef}
        className={`mermaid-container overflow-x-auto ${className}`}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    );
  }
  return (
    <div className={`text-[var(--text-secondary)] text-xs animate-pulse p-2 ${className}`}>
      Rendering diagram…
    </div>
  );
}
