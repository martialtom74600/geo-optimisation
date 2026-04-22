import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Activity,
  AlertCircle,
  Loader2,
  OctagonX,
  Radar,
  Search,
  Sparkles,
  Terminal,
  Trash2,
} from "lucide-react";
import { AnimatePresence } from "framer-motion";
import { motion } from "framer-motion";
import { GeoPlaybook } from "./components/GeoPlaybook";
import { HeroKpiCards } from "./components/HeroKpiCards";
import { LeadPipelineTable } from "./components/LeadPipelineTable";
import { OpportunityDrawer } from "./components/OpportunityDrawer";
import { ZoneScannerBar } from "./components/ZoneScannerBar";
import {
  cancelJob,
  deleteLead,
  fetchLeads,
  fetchStats,
  getJob,
  listJobs,
  startZoneJob,
  updateLeadCrm,
} from "./api";
import type { CrmStatus, JobActivityLine, Lead, SourcingJob, Stats } from "./types";

const CRM_LABEL: Record<string, string> = {
  new: "Nouveau",
  to_contact: "À contacter",
  won: "Gagné",
  lost: "Perdu",
};

const PROOF_LABEL: Record<string, string> = {
  optimized: "Optimisé",
  priority: "Priorité",
  unknown: "Inconnu",
};

type ActivityLine = { id: string; t: string; line: string };

function serverActivityToLines(log: JobActivityLine[], jobId: number): ActivityLine[] {
  return log.map((e, i) => ({
    id: `job-${jobId}-${e.at}-${i}`,
    t: e.at
      ? new Date(e.at).toLocaleTimeString("fr-FR", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      : "—",
    line: e.message,
  }));
}

function usePollJob(
  jobId: number | null,
  onUpdate: (job: SourcingJob) => void,
  onDone: () => void
) {
  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      try {
        const j = await getJob(jobId);
        onUpdate(j);
        if (
          j.status === "completed" ||
          j.status === "failed" ||
          j.status === "cancelled"
        ) {
          onDone();
          return;
        }
      } catch {
        /* ignore */
      }
    };
    void tick();
    const id = window.setInterval(tick, 1000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [jobId, onUpdate, onDone]);
}

export default function App() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [jobs, setJobs] = useState<SourcingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [cityInput, setCityInput] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [crmFilter, setCrmFilter] = useState<string>("");
  const [proofFilter, setProofFilter] = useState<string>("");
  const [listOrder, setListOrder] = useState<"" | "score_desc" | "score_asc">(
    ""
  );
  const [selected, setSelected] = useState<Lead | null>(null);
  const [pollId, setPollId] = useState<number | null>(null);
  const [liveJob, setLiveJob] = useState<SourcingJob | null>(null);
  const [activityLog, setActivityLog] = useState<ActivityLine[]>([]);
  const logScrollRef = useRef<HTMLDivElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const lastProgressRef = useRef("");
  const failureLoggedRef = useRef(false);
  const cancelledLoggedRef = useRef(false);

  const appendActivityLine = useCallback((line: string) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    setActivityLog((prev) => {
      if (prev.length && prev[prev.length - 1].line === trimmed) {
        return prev;
      }
      const t = new Date().toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      const next = [...prev, { id, t, line: trimmed }];
      return next.length > 200 ? next.slice(-200) : next;
    });
  }, []);

  // Dernière ligne toujours visible (effet « flux / IA qui écrit ») — useLayout = avant le paint
  useLayoutEffect(() => {
    const panel = logScrollRef.current;
    if (!panel) return;
    const pinBottom = () => {
      panel.scrollTop = panel.scrollHeight;
    };
    pinBottom();
    const id = requestAnimationFrame(() => {
      pinBottom();
      logEndRef.current?.scrollIntoView({ block: "end", behavior: "auto" });
    });
    return () => cancelAnimationFrame(id);
  }, [activityLog]);

  const [formCity, setFormCity] = useState("Annecy");
  const [formMaxTotal, setFormMaxTotal] = useState(40);
  const [formMaxPer, setFormMaxPer] = useState(8);
  const [formAuditAll, setFormAuditAll] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const loadAll = useCallback(async () => {
    setErr(null);
    setLoading(true);
    try {
      const [l, s, j] = await Promise.all([
        fetchLeads({
          crm_status: crmFilter || undefined,
          proof_status: proofFilter || undefined,
          city: cityFilter || undefined,
          q: q || undefined,
          order: listOrder || undefined,
        }),
        fetchStats(),
        listJobs(),
      ]);
      setLeads(l);
      setStats(s);
      setJobs(j);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Erreur chargement");
    } finally {
      setLoading(false);
    }
  }, [crmFilter, proofFilter, cityFilter, q, listOrder]);

  useEffect(() => {
    const t = window.setTimeout(() => setQ(qInput.trim()), 400);
    return () => window.clearTimeout(t);
  }, [qInput]);

  useEffect(() => {
    const t = window.setTimeout(
      () => setCityFilter(cityInput.trim()),
      400
    );
    return () => window.clearTimeout(t);
  }, [cityInput]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const refreshOnJobDone = useCallback(() => {
    void loadAll();
    setPollId(null);
    setLiveJob(null);
    lastProgressRef.current = "";
  }, [loadAll]);

  const onJobPollUpdate = useCallback(
    (j: SourcingJob) => {
      setLiveJob(j);
      setJobs((prev) => {
        const i = prev.findIndex((x) => x.id === j.id);
        if (i < 0) return [j, ...prev];
        const next = [...prev];
        next[i] = j;
        return next;
      });
      if (j.activity_log && j.activity_log.length > 0) {
        setActivityLog(serverActivityToLines(j.activity_log, j.id));
        if (j.progress_message) {
          lastProgressRef.current = j.progress_message;
        }
      } else if (j.progress_message && j.progress_message !== lastProgressRef.current) {
        lastProgressRef.current = j.progress_message;
        appendActivityLine(j.progress_message);
      }
      if (j.status === "failed" && j.error && !failureLoggedRef.current) {
        failureLoggedRef.current = true;
        appendActivityLine(`Erreur : ${j.error}`);
      }
      if (j.status === "cancelled" && !cancelledLoggedRef.current) {
        cancelledLoggedRef.current = true;
        const msg = j.error?.trim() || j.progress_message?.trim();
        appendActivityLine(
          msg && msg.length > 0 ? msg : "Recherche arrêtée sur demande."
        );
      }
    },
    [appendActivityLine]
  );

  usePollJob(pollId, onJobPollUpdate, refreshOnJobDone);

  const onStartZone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formCity.trim()) return;
    setSubmitting(true);
    setErr(null);
    try {
      const j = await startZoneJob({
        city: formCity.trim(),
        max_total: formMaxTotal,
        max_per_metier: formMaxPer,
        audit_all: formAuditAll,
      });
      failureLoggedRef.current = false;
      cancelledLoggedRef.current = false;
      lastProgressRef.current = j.progress_message || "";
      const t0 = new Date().toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      if (j.activity_log && j.activity_log.length > 0) {
        setActivityLog(serverActivityToLines(j.activity_log, j.id));
      } else {
        setActivityLog([
          {
            id: `job-${j.id}-start`,
            t: t0,
            line: `Lancement — job n°${j.id}, ville « ${j.city} », plafond ${j.max_total} prospect(s) au total, jusqu’à ${j.max_per_metier} site(s) par métier. Le détail de chaque étape arrive ci‑dessous dès que le serveur a démarré.`,
          },
          ...(j.progress_message
            ? [{ id: `job-${j.id}-0`, t: t0, line: j.progress_message.trim() }]
            : []),
        ]);
      }
      setJobs((prev) => [j, ...prev]);
      setLiveJob(j);
      setPollId(j.id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Lancement impossible");
    } finally {
      setSubmitting(false);
    }
  };

  const updateCrm = async (id: number, crm_status: CrmStatus) => {
    try {
      const updated = await updateLeadCrm(id, crm_status);
      setLeads((prev) => prev.map((l) => (l.id === id ? updated : l)));
      if (selected?.id === id) setSelected(updated);
      const s = await fetchStats();
      setStats(s);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "MàJ impossible");
    }
  };

  const removeLeadById = useCallback(async (id: number) => {
    if (
      !window.confirm(
        "Supprimer ce prospect de la base ? Cette action est définitive."
      )
    ) {
      return;
    }
    setErr(null);
    try {
      await deleteLead(id);
      setLeads((prev) => prev.filter((x) => x.id !== id));
      setSelected((s) => (s?.id === id ? null : s));
      const st = await fetchStats();
      setStats(st);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Suppression impossible");
    }
  }, []);

  const activeJob = useMemo(() => {
    if (liveJob && (liveJob.status === "running" || liveJob.status === "queued")) {
      return liveJob;
    }
    return (
      jobs.find((j) => j.status === "running" || j.status === "queued") ?? null
    );
  }, [jobs, liveJob]);

  const onCancelActiveJob = useCallback(async () => {
    if (!activeJob) return;
    setErr(null);
    setCancelling(true);
    try {
      await cancelJob(activeJob.id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Annulation impossible");
    } finally {
      setCancelling(false);
    }
  }, [activeJob]);

  const lastStatusTextForStaleRef = useRef("");
  const lastStatusAtRef = useRef(Date.now());
  const watchedRunningJobIdRef = useRef<number | null>(null);
  const [staleHint, setStaleHint] = useState<string | null>(null);

  useEffect(() => {
    if (!activeJob) {
      watchedRunningJobIdRef.current = null;
      setStaleHint(null);
      return;
    }
    if (watchedRunningJobIdRef.current !== activeJob.id) {
      watchedRunningJobIdRef.current = activeJob.id;
      lastStatusTextForStaleRef.current = "";
      lastStatusAtRef.current = Date.now();
    }
    const m = activeJob.progress_message;
    if (m && m !== lastStatusTextForStaleRef.current) {
      lastStatusTextForStaleRef.current = m;
      lastStatusAtRef.current = Date.now();
      setStaleHint(null);
    }
  }, [activeJob, activeJob?.id, activeJob?.progress_message]);

  useEffect(() => {
    if (!activeJob) return;
    const id = window.setInterval(() => {
      const silentMs = Date.now() - lastStatusAtRef.current;
      if (silentMs > 90_000) {
        const min = Math.max(1, Math.floor(silentMs / 60_000));
        setStaleHint(
          `Aucun nouveau message depuis ~${min} min. Souvent normal : moteur de recherche lent, site distante lent, ou file d’appels Groq. Si le job finit, tout va bien.`
        );
      } else {
        setStaleHint(null);
      }
    }, 6_000);
    return () => window.clearInterval(id);
  }, [activeJob]);

  return (
    <div className="min-h-screen flex items-start">
      <aside className="w-72 shrink-0 border-r border-zinc-800/80 bg-zinc-950/80 backdrop-blur flex flex-col h-[100dvh] max-h-[100dvh] min-h-0 sticky top-0 overflow-hidden">
        <div className="p-5 border-b border-zinc-800/80 shrink-0">
          <div className="flex items-center gap-2.5 mb-0.5">
            <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-glow ring-1 ring-white/10">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-display text-base font-bold tracking-tight text-white">
                GEO Prospector
              </h1>
              <p className="text-[10px] text-zinc-500 uppercase tracking-[0.2em]">
                CRM Sourcing
              </p>
            </div>
          </div>
        </div>

        <div className="p-3 border-b border-zinc-800/60 max-h-[min(32vh,14rem)] min-h-0 overflow-y-auto scroll-thin shrink-0">
          <div className="flex items-center gap-2 text-[10px] font-semibold text-zinc-500 uppercase tracking-widest mb-2 px-1">
            <Radar className="h-3 w-3" />
            Guide
          </div>
          <GeoPlaybook />
        </div>

        <div className="px-3 py-2 flex-1 min-h-0 min-w-0 flex flex-col overflow-hidden">
          <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/30 overflow-hidden flex flex-col flex-1 min-h-0 min-w-0">
            <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-zinc-800/60 bg-zinc-950/50 shrink-0">
              <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 shrink-0" />
                Journal
              </span>
              <button
                type="button"
                title="Vider le journal"
                className="p-1 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                onClick={() => {
                  setActivityLog([]);
                  lastProgressRef.current = "";
                }}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
            {/* hauteur plafonnée : le contenu ne pousse plus la barre ; scroll interne uniquement (flex: min-h auto sinon = hauteur du texte) */}
            <div
              ref={logScrollRef}
              className="min-h-0 flex-1 basis-0 overflow-y-auto scroll-thin overscroll-contain px-2 py-2 max-h-[min(50dvh,20rem)] text-[10px] leading-relaxed space-y-2.5"
            >
              {activityLog.length === 0 ? (
                <p className="text-zinc-500 px-1 leading-snug">
                  Les messages du run en cours s’affichent ici. Un sourcing peut
                  prendre plusieurs minutes.
                </p>
              ) : (
                activityLog.map((row) => (
                  <div key={row.id} className="flex gap-2.5 text-zinc-400">
                    <span className="text-zinc-600 shrink-0 tabular-nums font-mono text-[9px] pt-0.5">
                      {row.t}
                    </span>
                    <span className="text-zinc-200/90 break-words min-w-0">
                      {row.line}
                    </span>
                  </div>
                ))
              )}
              {/* ancre : scrollIntoView + scrollHeight pour coller le bas quand le texte se wrap */}
              <div ref={logEndRef} className="h-px w-full shrink-0" aria-hidden />
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0 bg-surface">
        <header className="h-14 shrink-0 border-b border-zinc-800/80 flex items-center justify-between px-4 sm:px-6 gap-3 bg-slate-950/50 backdrop-blur">
          <div className="flex items-center gap-2.5 min-w-0 text-zinc-500 text-xs sm:text-sm">
            <span className="text-zinc-400 font-medium hidden sm:inline">Filtres</span>
            <div className="relative flex-1 min-w-0 max-w-md">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-600" />
              <input
                className="w-full rounded-lg bg-zinc-950/60 border border-zinc-800 pl-8 pr-2 py-1.5 text-xs sm:text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500/40"
                placeholder="Recherche (nom, URL, métier)…"
                value={qInput}
                onChange={(e) => setQInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && setQ(qInput.trim())}
              />
            </div>
            <input
              className="w-20 sm:w-24 rounded-lg bg-zinc-950/60 border border-zinc-800 px-2 py-1.5 text-xs"
              placeholder="Ville"
              value={cityInput}
              onChange={(e) => setCityInput(e.target.value)}
            />
            <select
              className="hidden md:block rounded-lg bg-zinc-950/60 border border-zinc-800 px-2 py-1.5 text-xs max-w-[7rem]"
              value={crmFilter}
              onChange={(e) => setCrmFilter(e.target.value)}
            >
              <option value="">Statut</option>
              {Object.keys(CRM_LABEL).map((k) => (
                <option key={k} value={k}>
                  {CRM_LABEL[k]}
                </option>
              ))}
            </select>
            <select
              className="hidden lg:block rounded-lg bg-zinc-950/60 border border-zinc-800 px-2 py-1.5 text-xs max-w-[7.5rem]"
              value={proofFilter}
              onChange={(e) => setProofFilter(e.target.value)}
            >
              <option value="">Preuve</option>
              {Object.keys(PROOF_LABEL).map((k) => (
                <option key={k} value={k}>
                  {PROOF_LABEL[k]}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => void loadAll()}
              className="shrink-0 text-xs text-indigo-300 hover:text-white"
            >
              Actualiser
            </button>
          </div>
        </header>

        {activeJob && (
          <div className="shrink-0 border-b border-indigo-500/30 bg-gradient-to-r from-indigo-950/50 to-slate-950/90 px-4 py-2.5 flex flex-col gap-1.5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-3 sm:justify-between">
              <div className="flex items-center gap-2 shrink-0">
                <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                <div>
                  <p className="text-sm font-medium text-white">Sourcing en cours</p>
                  <p className="text-[10px] text-zinc-500">
                    {activeJob.city} — job n°{activeJob.id}
                  </p>
                </div>
              </div>
              <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-2 sm:flex-1 sm:min-w-0 sm:justify-end">
                <p className="text-[11px] text-zinc-300 sm:max-w-lg sm:text-right leading-snug order-2 sm:order-1">
                  {activeJob.progress_message || "En attente du serveur…"}
                </p>
                <button
                  type="button"
                  onClick={() => void onCancelActiveJob()}
                  disabled={cancelling || activeJob.cancel_requested}
                  className="shrink-0 order-1 sm:order-2 inline-flex items-center justify-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-500/10 px-2.5 py-1 text-[11px] font-medium text-rose-200 hover:bg-rose-500/20 disabled:opacity-50"
                >
                  {cancelling || activeJob.cancel_requested ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Arrêt…
                    </>
                  ) : (
                    <>
                      <OctagonX className="w-3.5 h-3.5" />
                      Arrêter
                    </>
                  )}
                </button>
              </div>
            </div>
            {staleHint && (
              <p className="text-[10px] text-amber-200/90 bg-amber-500/10 border border-amber-500/20 rounded-md px-2 py-1 leading-relaxed">
                {staleHint}
              </p>
            )}
          </div>
        )}

        {err && (
          <div className="mx-4 sm:mx-6 mt-3 flex items-center gap-2 text-sm text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {err}
          </div>
        )}

        <div className="flex-1 overflow-hidden flex min-h-0">
          <div className="flex-1 overflow-y-auto scroll-thin px-4 sm:px-6 py-6">
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
            >
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400/80 mb-1">
                Cockpit
              </p>
              <h2 className="font-display text-xl sm:text-2xl text-white font-semibold tracking-tight mb-1">
                Sourcing &amp; opportunités
              </h2>
              <p className="text-sm text-zinc-500 max-w-2xl mb-6">
                Les indicateurs clés, puis le scanner de zone et votre pipeline. Ouvrez un lead
                pour l’argumentaire commercial et les preuves techniques.
              </p>

              <HeroKpiCards stats={stats} />

              <ZoneScannerBar
                formCity={formCity}
                onFormCityChange={setFormCity}
                formMaxTotal={formMaxTotal}
                onFormMaxTotalChange={setFormMaxTotal}
                formMaxPer={formMaxPer}
                onFormMaxPerChange={setFormMaxPer}
                formAuditAll={formAuditAll}
                onFormAuditAllChange={setFormAuditAll}
                onSubmit={onStartZone}
                submitting={submitting}
              />

              <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-200">Pipeline des leads</h3>
                  <p className="text-xs text-zinc-500">Tri, statuts CRM, ouverture d’audit en un clic</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <label className="text-[10px] text-zinc-500 sm:not-sr-only">Tri</label>
                  <select
                    className="rounded-lg bg-zinc-950/50 border border-zinc-800 px-2 py-1.5 text-xs"
                    value={listOrder}
                    onChange={(e) =>
                      setListOrder(
                        (e.target.value || "") as "" | "score_desc" | "score_asc"
                      )
                    }
                  >
                    <option value="">Plus récents</option>
                    <option value="score_desc">Score opportunité (haut → bas)</option>
                    <option value="score_asc">Score opportunité (bas → haut)</option>
                  </select>
                  {loading && (
                    <span className="text-xs text-zinc-500 flex items-center gap-1">
                      <Activity className="w-3 h-3 animate-pulse" />
                      Chargement
                    </span>
                  )}
                </div>
              </div>

              <LeadPipelineTable
                leads={leads}
                loading={loading}
                onSelectLead={setSelected}
                onOpenAudit={setSelected}
                onCrmChange={updateCrm}
                onDelete={removeLeadById}
              />
            </motion.div>
          </div>

          <AnimatePresence>
            {selected && (
              <OpportunityDrawer
                key={selected.id}
                lead={selected}
                onClose={() => setSelected(null)}
                onUpdated={(l) => {
                  setLeads((prev) => prev.map((x) => (x.id === l.id ? l : x)));
                  setSelected(l);
                }}
                onDelete={() => void removeLeadById(selected.id)}
              />
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
