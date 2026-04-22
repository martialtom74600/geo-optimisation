import type { Lead, Stats } from "../types";

/** Une mission d’audit GEO facturée (hypothèse vente affichée au commercial). */
export const AUDIT_PIPELINE_VALUE_EUR = 1000;

export function highPotentialLeadCount(stats: Stats | null): number {
  if (!stats?.by_proof_status) return 0;
  return stats.by_proof_status.priority ?? 0;
}

export function estimatedPipelineValueEur(stats: Stats | null): number {
  return highPotentialLeadCount(stats) * AUDIT_PIPELINE_VALUE_EUR;
}

export type SalesGauge = { value: number; tier: "success" | "danger" | "neutral" };

/**
 * Jauge « vendeur » : sans schéma business exploitable (priorité) → rouge &lt; 30.
 * Avec preuve solide (optimisé) → vert côté visibilité machine.
 */
export function salesGaugeFromLead(lead: Lead): SalesGauge {
  if (lead.proof_status === "optimized" && lead.crawl_business_ok) {
    const geo = lead.score_opportunite_geo;
    const spread = geo != null ? Math.min(30, Math.round(geo * 0.25)) : 18;
    const v = Math.min(100, Math.max(68, 72 + spread));
    return { value: v, tier: "success" };
  }
  if (lead.proof_status === "priority") {
    const v = Math.min(
      28,
      8 +
        (lead.score_opportunite_geo != null
          ? Math.min(20, (100 - lead.score_opportunite_geo) / 5)
          : 18)
    );
    return { value: Math.round(v), tier: "danger" };
  }
  // unknown / non démontré : reste en zone faible (prospection)
  return { value: 24, tier: "danger" };
}

export function crmUi(lead: Lead): { label: string; badgeClass: string } {
  if (lead.crm_status === "won") {
    return {
      label: "Gagné",
      badgeClass:
        "bg-emerald-500/15 text-emerald-200 border border-emerald-500/35 shadow-sm shadow-emerald-500/10",
    };
  }
  if (lead.crm_status === "lost") {
    return {
      label: "Perdu",
      badgeClass: "bg-zinc-800/80 text-zinc-500 border border-zinc-700/60",
    };
  }
  if (lead.crm_status === "to_contact" && lead.contacted_at) {
    return {
      label: "Relancé",
      badgeClass:
        "bg-amber-500/12 text-amber-200 border border-amber-500/35",
    };
  }
  if (lead.crm_status === "to_contact") {
    return {
      label: "À contacter",
      badgeClass:
        "bg-indigo-500/18 text-indigo-200 border border-indigo-500/35",
    };
  }
  return {
    label: "Nouveau",
    badgeClass: "bg-slate-700/50 text-slate-200 border border-slate-600/40",
  };
}

/** Heuristique « lu par les LLM » : preuve structurée sur la home. */
export function isMachineReadableHome(lead: Lead): boolean {
  return lead.proof_status === "optimized" && lead.crawl_business_ok;
}
