import { ExternalLink, FileSearch, Trash2 } from "lucide-react";
import type { CrmStatus, Lead } from "../types";
import { ScoreGauge } from "./ScoreGauge";
import { crmUi, salesGaugeFromLead } from "../lib/leadDisplay";

const PROOF_LABEL: Record<string, string> = {
  optimized: "OK schéma",
  priority: "Priorité",
  unknown: "Inconnu",
};

const PROOF_BADGE: Record<string, string> = {
  optimized: "bg-emerald-500/12 text-emerald-200/95 border border-emerald-500/30",
  priority: "bg-rose-500/12 text-rose-200 border border-rose-500/40",
  unknown: "bg-amber-500/10 text-amber-200/90 border border-amber-500/25",
};

const CRM_FOR_SELECT: { value: CrmStatus; label: string }[] = [
  { value: "new", label: "Nouveau" },
  { value: "to_contact", label: "À contacter" },
  { value: "won", label: "Gagné" },
  { value: "lost", label: "Perdu" },
];

type Props = {
  leads: Lead[];
  loading: boolean;
  onSelectLead: (lead: Lead) => void;
  onOpenAudit: (lead: Lead) => void;
  onCrmChange: (id: number, crm: CrmStatus) => void;
  onDelete: (id: number) => void;
};

export function LeadPipelineTable({
  leads,
  loading,
  onSelectLead,
  onOpenAudit,
  onCrmChange,
  onDelete,
}: Props) {
  return (
    <div className="rounded-2xl border border-zinc-800/80 bg-slate-950/40 overflow-hidden shadow-card">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm min-w-[880px]">
          <thead>
            <tr className="border-b border-zinc-800/90 bg-slate-900/50 text-zinc-500 text-[10px] uppercase tracking-widest">
              <th className="p-3.5 pl-4 font-semibold w-[22%]">Entreprise</th>
              <th className="p-3.5 font-semibold w-28">Score IA</th>
              <th className="p-3.5 font-semibold w-[12%]">Métier</th>
              <th className="p-3.5 font-semibold w-[10%]">Ville</th>
              <th className="p-3.5 font-semibold">Pré-signal</th>
              <th className="p-3.5 font-semibold w-[11%]">Statut</th>
              <th className="p-3.5 pr-4 font-semibold w-[12%] text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {leads.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="p-12 text-center text-zinc-500">
                  Aucun lead. Lancez un scan de ville ou ajustez les filtres.
                </td>
              </tr>
            )}
            {leads.map((row) => {
              const gauge = salesGaugeFromLead(row);
              const { label: crmLabel, badgeClass: crmBadge } = crmUi(row);
              return (
                <tr
                  key={row.id}
                  className="border-b border-zinc-800/40 odd:bg-slate-950/20 even:bg-slate-900/10 hover:bg-indigo-500/[0.04] transition-colors cursor-pointer group/row"
                  onClick={() => onSelectLead(row)}
                >
                  <td className="p-3.5 pl-4 align-top">
                    <div className="font-medium text-zinc-100 group-hover/row:text-white">
                      {row.company_name}
                    </div>
                    <a
                      href={row.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-indigo-400/90 hover:text-indigo-300 hover:underline line-clamp-1 mt-0.5"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {row.url}
                      <ExternalLink className="h-3 w-3 shrink-0 opacity-50" />
                    </a>
                    {row.synthese_expert_geo && (
                      <p className="text-[10px] text-zinc-500 line-clamp-2 mt-1.5 max-w-md">
                        {row.synthese_expert_geo}
                      </p>
                    )}
                  </td>
                  <td className="p-3.5 align-middle">
                    <div className="flex justify-end pr-1">
                      <ScoreGauge gauge={gauge} />
                    </div>
                  </td>
                  <td className="p-3.5 text-zinc-400 align-top">{row.metier || "—"}</td>
                  <td className="p-3.5 text-zinc-400 align-top">{row.city || "—"}</td>
                  <td className="p-3.5 align-top">
                    <span
                      className={`inline-flex text-xs px-2.5 py-0.5 rounded-md font-medium ${PROOF_BADGE[row.proof_status] ?? "bg-zinc-800"}`}
                    >
                      {PROOF_LABEL[row.proof_status] ?? row.proof_status}
                    </span>
                  </td>
                  <td className="p-3.5 align-top">
                    <span
                      className={`inline-flex text-xs px-2.5 py-0.5 rounded-md font-medium ${crmBadge}`}
                    >
                      {crmLabel}
                    </span>
                  </td>
                  <td
                    className="p-3.5 pr-4 align-top text-right"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="inline-flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2">
                      <select
                        className="w-full sm:w-[8.5rem] text-xs bg-zinc-900/90 border border-zinc-700/60 rounded-lg px-2 py-1.5 text-zinc-200"
                        value={row.crm_status}
                        onChange={(e) =>
                          void onCrmChange(row.id, e.target.value as CrmStatus)
                        }
                      >
                        {CRM_FOR_SELECT.map((k) => (
                          <option key={k.value} value={k.value}>
                            {k.label}
                          </option>
                        ))}
                      </select>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => onOpenAudit(row)}
                          className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-indigo-500/35 bg-indigo-500/10 px-2.5 py-1.5 text-[11px] font-semibold text-indigo-200 hover:bg-indigo-500/20 hover:text-white transition"
                        >
                          <FileSearch className="h-3.5 w-3.5" />
                          Ouvrir l&apos;Audit
                        </button>
                        <button
                          type="button"
                          title="Supprimer de la base"
                          onClick={() => void onDelete(row.id)}
                          className="p-1.5 rounded-md text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
