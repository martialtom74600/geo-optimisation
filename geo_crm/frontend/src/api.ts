import type { Lead, LeadPatch, SourcingJob, Stats } from "./types";

const json = (r: Response) => {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json() as Promise<unknown>;
};

export async function fetchStats(): Promise<Stats> {
  return (await json(await fetch("/api/stats"))) as Stats;
}

export async function fetchLeads(params: {
  crm_status?: string;
  proof_status?: string;
  city?: string;
  q?: string;
  order?: "created_desc" | "score_desc" | "score_asc";
}): Promise<Lead[]> {
  const u = new URL("/api/leads", window.location.origin);
  for (const [k, v] of Object.entries(params)) {
    if (v) u.searchParams.set(k, v);
  }
  return (await json(await fetch(u))) as Lead[];
}

export async function deleteLead(id: number): Promise<void> {
  const r = await fetch(`/api/leads/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
}

export async function patchLead(id: number, body: LeadPatch): Promise<Lead> {
  return (await json(
    await fetch(`/api/leads/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  )) as Lead;
}

export async function updateLeadCrm(
  id: number,
  crm_status: Lead["crm_status"]
): Promise<Lead> {
  return patchLead(id, { crm_status });
}

export async function startZoneJob(body: {
  city: string;
  max_total: number;
  max_per_metier: number;
  audit_all: boolean;
}): Promise<SourcingJob> {
  return (await json(
    await fetch("/api/jobs/zone", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  )) as SourcingJob;
}

export async function listJobs(): Promise<SourcingJob[]> {
  return (await json(await fetch("/api/jobs"))) as SourcingJob[];
}

export async function getJob(id: number): Promise<SourcingJob> {
  return (await json(await fetch(`/api/jobs/${id}`))) as SourcingJob;
}

export async function cancelJob(id: number): Promise<SourcingJob> {
  return (await json(
    await fetch(`/api/jobs/${id}/cancel`, { method: "POST" })
  )) as SourcingJob;
}
