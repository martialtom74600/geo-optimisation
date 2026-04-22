import { Euro, Radar, Users } from "lucide-react";
import type { Stats } from "../types";
import {
  AUDIT_PIPELINE_VALUE_EUR,
  estimatedPipelineValueEur,
  highPotentialLeadCount,
} from "../lib/leadDisplay";

const eur = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

export function HeroKpiCards({ stats }: { stats: Stats | null }) {
  const total = stats?.total_leads ?? 0;
  const hot = highPotentialLeadCount(stats);
  const pipe = estimatedPipelineValueEur(stats);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <div className="group relative overflow-hidden rounded-2xl border border-slate-700/60 bg-gradient-to-br from-slate-900/90 via-slate-900/70 to-zinc-950 p-5 shadow-card transition hover:border-indigo-500/30 hover:shadow-glow">
        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-indigo-500/10 blur-2xl" />
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Total leads sourcés
            </p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-white tracking-tight">
              {total}
            </p>
            <p className="mt-1 text-xs text-zinc-500">Base commerciale active</p>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-500/25">
            <Users className="h-5 w-5" />
          </div>
        </div>
      </div>

      <div className="group relative overflow-hidden rounded-2xl border border-slate-700/60 bg-gradient-to-br from-slate-900/90 via-rose-950/20 to-zinc-950 p-5 shadow-card transition hover:border-rose-500/25">
        <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-rose-500/10 blur-2xl" />
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Cibles haut potentiel
            </p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-rose-100 tracking-tight">
              {hot}
            </p>
            <p className="mt-1 text-xs text-rose-200/70">
              Sans JSON-LD / schéma business exploitable = opportunité d’audit
            </p>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30">
            <Radar className="h-5 w-5" />
          </div>
        </div>
      </div>

      <div className="group relative overflow-hidden rounded-2xl border border-slate-700/60 bg-gradient-to-br from-slate-900/90 via-emerald-950/25 to-zinc-950 p-5 shadow-card transition hover:border-emerald-500/25">
        <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-emerald-500/10 blur-2xl" />
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Valeur du pipeline
            </p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-emerald-200 tracking-tight">
              {eur.format(pipe)}
            </p>
            <p className="mt-1 text-xs text-emerald-200/60">
              Hypothèse : 1 mission type ≈ {eur.format(AUDIT_PIPELINE_VALUE_EUR)} × {hot} cible(s) prioritaires
            </p>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30">
            <Euro className="h-5 w-5" />
          </div>
        </div>
      </div>
    </div>
  );
}
