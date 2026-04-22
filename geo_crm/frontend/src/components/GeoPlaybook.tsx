import { BookOpen, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

export function GeoPlaybook() {
  const [open, setOpen] = useState(true);
  return (
    <div className="mx-4 mb-3 rounded-xl border border-indigo-500/20 bg-indigo-950/20 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-indigo-500/10"
      >
        {open ? (
          <ChevronDown className="w-4 h-4 text-indigo-400 shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-indigo-400 shrink-0" />
        )}
        <BookOpen className="w-4 h-4 text-indigo-300 shrink-0" />
        <span className="text-xs font-semibold text-indigo-200/95">
          Qu&apos;est-ce que le GEO ?
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3 text-[11px] leading-relaxed text-zinc-400 space-y-2 border-t border-indigo-500/10 pt-2">
          <p className="text-zinc-300">
            <strong className="text-zinc-200">GEO</strong> (Generative Engine
            Optimization) vise à être recommandé dans les{" "}
            <strong className="text-zinc-200">réponses des IA</strong> (ChatGPT,
            Gemini, Perplexity…) et les résumés sans clic, pas seulement à être
            #1 sur Google classique.
          </p>
          <p>
            Les moteurs utilisent des{" "}
            <strong>signaux structurés</strong> (JSON-LD{" "}
            <code className="text-indigo-300">LocalBusiness</code>,{" "}
            <code className="text-indigo-300">Organization</code>, cohérence
            titre/H1) pour « comprendre » une entreprise locale. Sans ça, le
            site est souvent <strong>transparent</strong> pour ces systèmes.
          </p>
          <p>
            Ce CRM analyse <strong>chaque site</strong> : données structurées,
            exploitabilité par les LLM, signal local — puis propose un{" "}
            <strong>score d&apos;opportunité</strong> et des actions
            prioritaires pour ton argumentaire commercial.
          </p>
        </div>
      )}
    </div>
  );
}
