import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Bot,
  Check,
  Code2,
  Copy,
  Gift,
  HeartPulse,
  Mail,
  StickyNote,
  Target,
  Trash2,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { patchLead } from "../api";
import { isMachineReadableHome } from "../lib/leadDisplay";
import type { Lead } from "../types";
import { EmailTemplateModal } from "./EmailTemplateModal";
import { JsonCodeBlock } from "./JsonCodeBlock";

type TabId = "sante" | "vente" | "cadeau";

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }
}

const tabs: { id: TabId; label: string; icon: typeof HeartPulse }[] = [
  { id: "sante", label: "Santé IA", icon: HeartPulse },
  { id: "vente", label: "Arsenal de vente", icon: Target },
  { id: "cadeau", label: "Le cadeau", icon: Gift },
];

export function OpportunityDrawer({
  lead,
  onClose,
  onUpdated,
  onDelete,
}: {
  lead: Lead;
  onClose: () => void;
  onUpdated: (l: Lead) => void;
  onDelete: () => void;
}) {
  const [tab, setTab] = useState<TabId>("sante");
  const [notes, setNotes] = useState(lead.user_notes ?? "");
  const [next, setNext] = useState(lead.next_action ?? "");
  const [saving, setSaving] = useState(false);
  const [emailModal, setEmailModal] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);

  useEffect(() => {
    setTab("sante");
  }, [lead.id]);

  useEffect(() => {
    setNotes(lead.user_notes ?? "");
    setNext(lead.next_action ?? "");
  }, [lead.id, lead.user_notes, lead.next_action]);

  const saveCrmFields = useCallback(async () => {
    setSaving(true);
    try {
      const updated = await patchLead(lead.id, {
        user_notes: notes || null,
        next_action: next || null,
      });
      onUpdated(updated);
    } finally {
      setSaving(false);
    }
  }, [lead.id, notes, next, onUpdated]);

  const machineOk = isMachineReadableHome(lead);
  const risque = lead.risque_marche?.trim();
  const hook = lead.hook_email?.trim();
  const jsonLd = lead.json_ld_suggestion;

  return (
    <motion.aside
      initial={{ x: 48, opacity: 0.9 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 28, opacity: 0 }}
      transition={{ type: "spring", damping: 34, stiffness: 380 }}
      className="w-[min(100vw-0.5rem,440px)] shrink-0 border-l border-zinc-800/80 bg-zinc-950/95 flex flex-col shadow-2xl z-20 backdrop-blur-md"
    >
        <EmailTemplateModal open={emailModal} lead={lead} onClose={() => setEmailModal(false)} />
        <div className="h-16 flex items-center justify-between px-4 border-b border-zinc-800/80 bg-gradient-to-r from-slate-950/90 to-zinc-950/80">
          <div className="min-w-0 pr-2">
            <p className="text-[10px] uppercase tracking-widest text-indigo-400/80 font-semibold">
              Audit & pitch
            </p>
            <h3 className="font-display text-base font-semibold truncate text-white">
              {lead.company_name}
            </h3>
            {lead.score_opportunite_geo != null && (
              <p className="text-[11px] text-zinc-500">
                Potentiel commercial (moteur interne){" "}
                <span className="text-rose-200 font-semibold tabular-nums">
                  {lead.score_opportunite_geo}
                </span>
                /100
              </p>
            )}
          </div>
          <div className="flex items-center gap-0.5 shrink-0">
            <button
              type="button"
              title="Supprimer de la base"
              onClick={() => onDelete()}
              className="p-2 rounded-lg hover:bg-rose-500/15 text-zinc-500 hover:text-rose-300 transition"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              type="button"
              title="Fermer"
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="px-2 pt-2 pb-0 border-b border-zinc-800/60">
          <div className="flex gap-0.5 p-0.5 rounded-xl bg-zinc-900/80 border border-zinc-800/80">
            {tabs.map((t) => {
              const Icon = t.icon;
              const on = tab === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTab(t.id)}
                  className={`flex-1 min-w-0 flex items-center justify-center gap-1.5 py-2 px-1 rounded-lg text-[11px] font-semibold transition ${
                    on
                      ? "bg-indigo-600/90 text-white shadow-md"
                      : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" />
                  <span className="hidden sm:inline truncate">{t.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto scroll-thin px-4 py-4 space-y-4">
          <AnimatePresence mode="wait">
            {tab === "sante" && (
              <motion.section
                key="sante"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18 }}
                className="space-y-4"
              >
                <div
                  className={`rounded-2xl border p-4 ${
                    machineOk
                      ? "border-emerald-500/35 bg-gradient-to-br from-emerald-950/40 to-zinc-950/30"
                      : "border-rose-500/35 bg-gradient-to-br from-rose-950/35 to-zinc-950/30"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                    <Bot className="h-3.5 w-3.5" />
                    Visibilité machine (extrait du crawl)
                  </div>
                  <div className="flex items-center gap-4">
                    <div
                      className={`h-20 w-20 shrink-0 rounded-2xl flex items-center justify-center text-2xl font-black border-2 ${
                        machineOk
                          ? "border-emerald-400/60 text-emerald-200 bg-emerald-500/10"
                          : "border-rose-500/50 text-rose-200 bg-rose-500/10"
                      }`}
                    >
                      {machineOk ? "OK" : "!"}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">
                        Ce site est-il &quot;lu&quot; par ChatGPT / Claude ?
                      </p>
                      <p className="text-sm text-zinc-300 mt-1 leading-relaxed">
                        {machineOk ? (
                          <>
                            <span className="text-emerald-300/95">Oui, signaux forts :</span> schéma
                            business cohérent côté page d’accueil — moins d’angle d’audit
                            &quot;urgent&quot; sauf refonte.
                          </>
                        ) : (
                          <>
                            <span className="text-rose-200/90">Plutôt non ou fragile :</span> manque
                            de balisage structuré exploitable — c’est votre levier de
                            conversation.
                          </>
                        )}
                      </p>
                    </div>
                  </div>
                </div>

                {risque ? (
                  <div className="rounded-xl border-l-4 border-rose-500/60 bg-rose-950/25 border border-rose-500/20 p-3">
                    <div className="flex items-center gap-2 text-rose-200 font-semibold text-sm mb-1">
                      <AlertTriangle className="h-4 w-4" />
                      Risque de marché (Génération IA)
                    </div>
                    <p className="text-sm text-rose-100/90 leading-relaxed whitespace-pre-wrap">
                      {risque}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-zinc-500 border border-dashed border-zinc-800 rounded-lg p-3">
                    Pas encore de texte de risque — relancez l’analyse côté pipeline si besoin.
                  </p>
                )}

                {lead.synthese_expert_geo?.trim() && (
                  <div className="rounded-lg border border-indigo-500/25 bg-indigo-950/25 p-3">
                    <p className="text-[10px] font-bold uppercase text-indigo-300/90 mb-1.5">
                      Contexte
                    </p>
                    <p className="text-sm text-zinc-200 leading-relaxed">{lead.synthese_expert_geo}</p>
                  </div>
                )}
              </motion.section>
            )}

            {tab === "vente" && (
              <motion.section
                key="vente"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18 }}
                className="space-y-4"
              >
                <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-b from-indigo-950/40 to-slate-950/40 p-4 shadow-inner">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-300/90 mb-2 flex items-center gap-1.5">
                    <Mail className="h-3.5 w-3.5" />
                    Hook email (Génération IA)
                  </p>
                  {hook ? (
                    <p className="text-sm text-zinc-100 leading-relaxed whitespace-pre-wrap font-medium">
                      {hook}
                    </p>
                  ) : (
                    <p className="text-sm text-zinc-500">Aucun hook — lancez l’enrichissement du lead.</p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => setEmailModal(true)}
                  className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl font-semibold text-sm text-white bg-indigo-600 hover:bg-indigo-500 border border-indigo-400/20 shadow-glow transition hover:scale-[1.01] active:scale-[0.99]"
                >
                  <Mail className="h-4 w-4" />
                  Générer un email complet
                </button>
                <p className="text-[11px] text-zinc-500 text-center">
                  Ouvre un modèle d’e-mail prêt à copier, avec l’accroche intégrée.
                </p>
              </motion.section>
            )}

            {tab === "cadeau" && (
              <motion.section
                key="cadeau"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18 }}
                className="space-y-3"
              >
                <p className="text-xs text-zinc-500 flex items-center gap-2">
                  <Code2 className="h-3.5 w-3.5" />
                  JSON-LD proposé — preuve immédiate de valeur (copier / coller côté client).
                </p>
                {jsonLd ? (
                  <>
                    <div className="relative rounded-xl border border-zinc-700/60 bg-[#0c0c0c] overflow-hidden ring-1 ring-white/[0.04] max-h-72">
                      <div className="px-2.5 py-1.5 border-b border-zinc-800/80 flex items-center justify-between gap-2 bg-zinc-900/50">
                        <span className="text-[9px] font-mono uppercase tracking-widest text-zinc-500">
                          JSON-LD
                        </span>
                      </div>
                      <div className="p-0 overflow-y-auto max-h-[calc(18rem-2.25rem)] scroll-thin">
                        <JsonCodeBlock code={jsonLd} />
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={async () => {
                        await copyText(jsonLd);
                        setCodeCopied(true);
                        window.setTimeout(() => setCodeCopied(false), 2000);
                      }}
                      className="w-full flex items-center justify-center gap-2 py-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 border border-emerald-400/25 shadow-lg transition hover:scale-[1.01] active:scale-[0.99]"
                    >
                      {codeCopied ? (
                        <>
                          <Check className="h-5 w-5" />
                          Code copié
                        </>
                      ) : (
                        <>
                          <Copy className="h-5 w-5" />
                          Copier le code
                        </>
                      )}
                    </button>
                  </>
                ) : (
                  <p className="text-sm text-zinc-500 border border-dashed border-zinc-800 rounded-lg p-4 text-center">
                    Aucun snippet JSON-LD généré pour ce prospect.
                  </p>
                )}

                {lead.faille_technique && (
                  <div>
                    <p className="text-[10px] text-zinc-500 uppercase mb-1">Détail technique</p>
                    <p className="text-xs text-zinc-400 whitespace-pre-wrap leading-relaxed">
                      {lead.faille_technique}
                    </p>
                  </div>
                )}
              </motion.section>
            )}
          </AnimatePresence>
        </div>

        <div className="shrink-0 border-t border-zinc-800/80 p-4 bg-zinc-950/80">
          <div className="flex items-center gap-2 text-xs font-medium text-zinc-500 mb-2">
            <StickyNote className="w-3.5 h-3.5" />
            Notes CRM
          </div>
          <textarea
            className="w-full min-h-[64px] rounded-lg bg-zinc-900/80 border border-zinc-800 px-2 py-1.5 text-xs text-zinc-200"
            placeholder="Objections, prochaine étape, rappel…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={() => void saveCrmFields()}
          />
          <div className="mt-2 flex items-center gap-2 text-xs text-zinc-500">
            <span>Prochaine action</span>
          </div>
          <input
            className="w-full mt-0.5 rounded-lg bg-zinc-900/80 border border-zinc-800 px-2 py-1.5 text-xs"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            onBlur={() => void saveCrmFields()}
            placeholder="ex. Relance mardi, envoi preuve…"
          />
          <button
            type="button"
            disabled={saving}
            onClick={() => void saveCrmFields()}
            className="mt-2 text-[11px] text-indigo-300 hover:text-white"
          >
            {saving ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>

        {lead.error && (
          <p className="mx-4 mb-3 text-xs text-amber-200 bg-amber-500/10 border border-amber-500/25 rounded-lg p-2">
            {lead.error}
          </p>
        )}
    </motion.aside>
  );
}
