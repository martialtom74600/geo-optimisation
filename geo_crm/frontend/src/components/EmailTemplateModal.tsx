import { Mail, X } from "lucide-react";
import { useEffect, useId } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import type { Lead } from "../types";

function buildEmailBody(lead: Lead, hook: string): string {
  const lines = [
    "Bonjour,",
    "",
    hook.trim() || "[Accroche — à personnaliser]",
    "",
    `J’ai analysé le site de ${lead.company_name} (${lead.url}) dans le contexte de ${lead.metier || "votre activité"}${lead.city ? ` à ${lead.city}` : ""}.`,
    "",
    "Nous accompagnons les entreprises locales pour qu’elles soient correctement comprises par les moteurs et assistants (ce qui impacte directement visibilité et prises de contact).",
    "",
    "Seriez-vous ouvert·e à un court échange cette semaine ?",
    "",
    "Cordialement,",
    "[Votre prénom]",
    "[Lien calendrier ou téléphone]",
  ];
  return lines.join("\n");
}

export function EmailTemplateModal({
  open,
  lead,
  onClose,
}: {
  open: boolean;
  lead: Lead;
  onClose: () => void;
}) {
  const titleId = useId();
  const hook = lead.hook_email?.trim() || "";
  const body = buildEmailBody(lead, hook);
  const subject = `Proposition — visibilité IA / GEO (${lead.company_name})`;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (typeof document === "undefined") return null;

  return createPortal(
    <AnimatePresence>
      {open && (
        <div
          className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-4 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
        >
          <motion.button
            type="button"
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-label="Fermer"
          />
          <motion.div
            className="relative w-full max-w-lg rounded-2xl border border-zinc-700/80 bg-zinc-950 shadow-2xl max-h-[min(90vh,640px)] flex flex-col"
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ type: "spring", damping: 28, stiffness: 320 }}
          >
            <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-zinc-800/80">
              <div className="flex items-center gap-2 min-w-0">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-300">
                  <Mail className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <h2 id={titleId} className="text-sm font-semibold text-white truncate">
                    Email type prêt à envoyer
                  </h2>
                  <p className="text-[11px] text-zinc-500 truncate">{lead.company_name}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-800"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="px-4 py-3 space-y-2 overflow-y-auto scroll-thin flex-1 min-h-0">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-0.5">Objet</p>
                <p className="text-sm text-zinc-200 font-medium">{subject}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-0.5">Corps</p>
                <pre className="whitespace-pre-wrap text-xs text-zinc-300 leading-relaxed font-sans bg-zinc-900/50 border border-zinc-800/80 rounded-lg p-3 max-h-56 overflow-y-auto">
                  {body}
                </pre>
              </div>
            </div>
            <div className="px-4 py-3 border-t border-zinc-800/80 flex flex-col sm:flex-row gap-2 sm:justify-end">
              <button
                type="button"
                onClick={async () => {
                  const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
                  window.location.href = mailto;
                }}
                className="order-1 sm:order-2 inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2.5"
              >
                Ouvrir le client mail
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(
                      `Objet: ${subject}\n\n${body}`
                    );
                  } catch {
                    /* ignore */
                  }
                }}
                className="order-2 sm:order-1 inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-600 text-sm text-zinc-200 px-4 py-2.5 hover:bg-zinc-800/80"
              >
                Copier tout
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
