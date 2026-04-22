export type CrmStatus = "new" | "to_contact" | "won" | "lost";
export type ProofStatus = "optimized" | "priority" | "unknown";

export interface Lead {
  id: number;
  company_name: string;
  url: string;
  metier: string;
  city: string;
  title_serp: string;
  crm_status: CrmStatus;
  proof_status: ProofStatus;
  skip_ia_reason: string | null;
  error: string | null;
  risque_marche: string | null;
  faille_technique: string | null;
  hook_email: string | null;
  json_ld_suggestion: string | null;
  synthese_expert_geo: string | null;
  score_opportunite_geo: number | null;
  geo_dim_structured: string | null;
  geo_dim_llm: string | null;
  geo_dim_local: string | null;
  actions_prioritaires_json: string | null;
  user_notes: string | null;
  next_action: string | null;
  contacted_at: string | null;
  crawl_business_ok: boolean;
  sourcing_job_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface LeadPatch {
  crm_status?: CrmStatus;
  user_notes?: string | null;
  next_action?: string | null;
  contacted_at?: string | null;
}

export interface JobActivityLine {
  at: string;
  message: string;
}

export interface SourcingJob {
  id: number;
  city: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  cancel_requested?: boolean;
  progress_message: string;
  /** Journal serveur (texte pour humains, horodatage ISO). */
  activity_log?: JobActivityLine[];
  error: string | null;
  lead_count: number;
  max_total: number;
  max_per_metier: number;
  audit_all: boolean;
  created_at: string;
  completed_at: string | null;
}

export interface Stats {
  total_leads: number;
  by_crm_status: Record<string, number>;
  by_proof_status: Record<string, number>;
}
