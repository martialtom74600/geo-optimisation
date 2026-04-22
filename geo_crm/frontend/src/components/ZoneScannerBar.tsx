import { Activity, ChevronDown, MapPin, Radar, Sparkles, Tags } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import type { MetierCategory } from "../types";

type Props = {
  metierCategories: MetierCategory[];
  formMetierCategory: string;
  onFormMetierCategoryChange: (id: string) => void;
  formCity: string;
  onFormCityChange: (v: string) => void;
  formMaxTotal: number;
  onFormMaxTotalChange: (n: number) => void;
  formMaxPer: number;
  onFormMaxPerChange: (n: number) => void;
  formAuditAll: boolean;
  onFormAuditAllChange: (v: boolean) => void;
  onSubmit: (e: React.FormEvent) => void;
  submitting: boolean;
};

export function ZoneScannerBar({
  metierCategories,
  formMetierCategory,
  onFormMetierCategoryChange,
  formCity,
  onFormCityChange,
  formMaxTotal,
  onFormMaxTotalChange,
  formMaxPer,
  onFormMaxPerChange,
  formAuditAll,
  onFormAuditAllChange,
  onSubmit,
  submitting,
}: Props) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  return (
    <motion.div
      layout
      className="relative mb-8 rounded-2xl border border-slate-700/70 bg-gradient-to-b from-slate-900/95 via-zinc-950/90 to-slate-950/95 p-1 shadow-glow"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <div
        className="pointer-events-none absolute -inset-px rounded-2xl bg-gradient-to-r from-indigo-500/12 via-rose-500/5 to-emerald-500/10 opacity-60"
        aria-hidden
      />
      <form
        onSubmit={onSubmit}
        className="relative rounded-[15px] border border-slate-800/80 bg-slate-950/80 px-4 py-5 sm:px-6 sm:py-6"
      >
        <div className="flex flex-col items-center text-center gap-1 mb-4">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/25 bg-indigo-500/10 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-widest text-indigo-200/90">
            <Sparkles className="h-3 w-3" />
            Sourcing ciblé
          </div>
          <h2 className="font-display text-lg sm:text-xl text-white tracking-tight">
            Aspirateur de territoire
          </h2>
          <p className="text-sm text-zinc-500 max-w-lg">
            Catégorie d’activité + ville : le moteur enchaîne plusieurs intitulés (ex. « Restaurant »,
            « Traiteur ») pour couvrir toute la zone, puis filtre par domaine et analyse.
          </p>
        </div>

        <div className="mx-auto max-w-3xl">
          <div className="mb-3">
            <label className="sr-only" htmlFor="metier-cat">
              Secteur d’activité
            </label>
            <div className="relative">
              <Tags
                className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500"
                aria-hidden
              />
              <select
                id="metier-cat"
                className="w-full appearance-none rounded-xl border border-zinc-700/80 bg-zinc-950/90 pl-11 pr-10 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50"
                value={formMetierCategory}
                onChange={(e) => onFormMetierCategoryChange(e.target.value)}
                disabled={submitting || !metierCategories.length}
              >
                {(metierCategories.length ? metierCategories : [{ id: "high_ticket", label: "—" }]).map(
                  (c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  )
                )}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
            </div>
            <p className="text-[11px] text-zinc-600 mt-1.5 pl-0.5">
              Chaque option lance une série de requêtes ciblées (restaurants, bars, etc. pour
              &quot;Restauration&quot;).
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 sm:items-stretch sm:gap-0">
            <div className="relative flex-1 min-w-0">
              <MapPin
                className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500"
                aria-hidden
              />
              <input
                className="w-full rounded-xl sm:rounded-l-xl sm:rounded-r-none border border-zinc-700/80 bg-zinc-950/90 pl-11 pr-4 py-3.5 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50 transition-shadow"
                value={formCity}
                onChange={(e) => onFormCityChange(e.target.value)}
                placeholder="Ville cible, ex. Annecy, Lyon…"
                autoComplete="off"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="group sm:w-[min(100%,200px)] shrink-0 flex items-center justify-center gap-2.5 py-3.5 px-6 rounded-xl sm:rounded-l-none sm:rounded-r-xl font-semibold text-sm text-white bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-glow border border-indigo-400/20 transition-all duration-200 hover:scale-[1.01] active:scale-[0.99]"
            >
              {submitting ? (
                <Activity className="h-4 w-4 animate-spin" />
              ) : (
                <Radar className="h-4 w-4 transition group-hover:rotate-12" />
              )}
              Scanner la ville
            </button>
          </div>

          <div className="mt-3 flex justify-center">
            <button
              type="button"
              onClick={() => setDetailsOpen((o) => !o)}
              className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition"
            >
              <ChevronDown
                className={`h-3.5 w-3.5 transition ${detailsOpen ? "rotate-180" : ""}`}
              />
              Paramètres avancés
            </button>
          </div>

          {detailsOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-zinc-800/80">
                <div>
                  <label className="text-[11px] text-zinc-500 block mb-1">
                    Plafond total (prospects)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={2000}
                    className="w-full rounded-lg bg-zinc-950/80 border border-zinc-700/60 px-3 py-2 text-sm"
                    value={formMaxTotal}
                    onChange={(e) => onFormMaxTotalChange(+e.target.value || 1)}
                  />
                </div>
                <div>
                  <label className="text-[11px] text-zinc-500 block mb-1">
                    Par métier
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    className="w-full rounded-lg bg-zinc-950/80 border border-zinc-700/60 px-3 py-2 text-sm"
                    value={formMaxPer}
                    onChange={(e) => onFormMaxPerChange(+e.target.value || 1)}
                  />
                </div>
                <label className="sm:col-span-2 flex items-start gap-2.5 text-xs text-zinc-400 cursor-pointer rounded-lg border border-zinc-800/60 bg-zinc-950/50 px-3 py-2.5">
                  <input
                    type="checkbox"
                    className="mt-0.5 rounded border-zinc-600 text-indigo-500 focus:ring-indigo-500/40"
                    checked={formAuditAll}
                    onChange={(e) => onFormAuditAllChange(e.target.checked)}
                  />
                  <span>
                    <span className="text-zinc-200 font-medium">Mode exhaustif (IA sur tous)</span>
                    <span className="block text-zinc-500 mt-0.5">
                      Audite aussi les sites déjà &quot;optimisés&quot; — plus de requêtes, plus de
                      coût Groq.
                    </span>
                  </span>
                </label>
              </div>
            </motion.div>
          )}
        </div>
      </form>
    </motion.div>
  );
}
