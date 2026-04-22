"""
Interface CLI (Typer) : mode ciblé (métier + ville) ou mode zone (--zone).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax

from geo_stealth_prospector.audit_groq import audit_leads_concurrent
from geo_stealth_prospector.config import Settings
from geo_stealth_prospector.crawl_proof import crawl_leads_concurrent
from geo_stealth_prospector.duck_search import search_leads_furtif
from geo_stealth_prospector.export_leads import export_csv, export_json
from geo_stealth_prospector.lead_dedupe import dedupe_leads_by_registered_domain
from geo_stealth_prospector.models import CrawlResult, LeadRecord
from geo_stealth_prospector.naming import derive_company_name
from geo_stealth_prospector.profession_categories import resolve_zone_metiers
from geo_stealth_prospector.zone_sourcing import zone_sourcing_multimetier

app = typer.Typer(
    name="geo-stealth",
    help="Sourcing furtif (DuckDuckGo HTML) + crawl + audits GEO (Groq). Mode --zone = liste high-ticket.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console(stderr=True)
LOG = logging.getLogger("geo_stealth_prospector")


def _setup_log(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _jsonld_pill(c: CrawlResult | None) -> str:
    """Pastille visuelle d'état factuel (JSON-LD / schéma business sur la home)."""
    if c is None:
        return "[red]● JSON-LD[/] [dim](aucune mesure — mode sourcing seul / erreur interne)[/]"
    if c.error and not c.page_fetched:
        return f"[red]● JSON-LD[/] [dim](page non lue : {c.error})[/]"
    if c.has_relevant_business_schema:
        return (
            "[green]● JSON-LD[/] [green]LocalBusiness/Organization (ou équivalent) détecté sur la home[/]"
        )
    if c.has_jsonld_script and c.jsonld_types_found:
        ts = ", ".join(c.jsonld_types_found[:8])
        if len(c.jsonld_types_found) > 8:
            ts += "…"
        return f"[red]● JSON-LD[/] [dim](script présent, types: {ts} — pas de schéma business retenu)[/]"
    if c.has_jsonld_script:
        return "[red]● JSON-LD[/] [dim](script present mais contenu non exploitable / vide)[/]"
    return "[red]● JSON-LD[/] [dim](aucun application/ld+json sur la home)[/]"


def _print_results(
    rows: list[LeadRecord], *, sourcing_only: bool = False, zone_mode: bool = False
) -> None:
    for r in rows:
        if r.error and not r.audit and r.skip_ia_reason is None:
            crawl_line = f"{_jsonld_pill(r.crawl)}\n\n" if r.crawl else ""
            p = Panel(
                f"{crawl_line}[bold red]Erreur audit :[/] {r.error}\n[dim]{r.url}[/]",
                title=f"{r.source_rank:02d} · [bold]{r.company_name}[/]",
                border_style="red",
            )
            console.print(p)
        elif (r.skip_ia_reason or "") == "schema_ok" and r.crawl:
            p = Panel(
                f"{_jsonld_pill(r.crawl)}\n\n[green]Optimisé — schéma business détecté, aucun appel Groq (cash machine).[/]",
                title=f"{r.source_rank:02d} · {r.company_name} — [link={r.url}]{r.url}[/]",
                subtitle=f"{r.metier} · {r.city}",
                border_style="green",
            )
            console.print(p)
        elif sourcing_only or (not r.audit and not r.error and r.skip_ia_reason is None):
            snippet = f"[dim]{r.title}[/]\n" if r.title else ""
            p = Panel(
                f"{snippet}[link={r.url}]{r.url}[/]\n[dim]Sourcing uniquement (pas d'audit / crawl).[/]",
                title=f"{r.source_rank:02d} · [bold]{r.company_name}[/]",
                subtitle=f"{r.metier} · {r.city}",
                border_style="cyan",
            )
            console.print(p)
        else:
            if r.audit:
                body = (
                    f"{_jsonld_pill(r.crawl)}\n\n"
                    f"[bold]Risque de marché[/]\n{r.audit.risque_marche}\n\n"
                    f"[bold]Faille technique (factuel)[/]\n{r.audit.faille_technique}\n\n"
                    f"[bold]Hook email[/]\n[green]{r.audit.hook_email}[/]"
                )
            else:
                body = f"{_jsonld_pill(r.crawl)}\n\n" + (r.error or "Pas d'audit (clé manquante).")
            p = Panel(
                body,
                title=f"{r.source_rank:02d} · {r.company_name} — [link={r.url}]{r.url}[/]",
                subtitle=f"{r.metier} · {r.city}",
                border_style="blue",
            )
            console.print(p)
            if r.audit and (r.audit.json_ld_suggestion or "").strip():
                console.print(
                    f"[dim]— {r.company_name} : snippet [bold]LocalBusiness[/] (à offrir en copier/coller) —[/]"
                )
                console.print(
                    Syntax(
                        r.audit.json_ld_suggestion.strip(),
                        "json",
                        theme="monokai",
                        word_wrap=True,
                    )
                )
                console.print()


@app.command()
def run_cmd(
    metier: Optional[str] = typer.Argument(
        default=None, help="Métier ciblé (requis en mode ciblé ; optionnel avec --zone pour un seul métier)."
    ),
    ville: Optional[str] = typer.Argument(
        default=None, help="Ville (requise en mode ciblé sans --zone, ignorée si --zone seul)."
    ),
    zone: Optional[str] = typer.Option(
        None,
        "--zone",
        "-z",
        help="Mode aspirateur : la ville cible ; sans MÉTIER, utilise --categorie ou la liste high-ticket.",
    ),
    categorie: Optional[str] = typer.Option(
        None,
        "--categorie",
        "--cat",
        help="Mode --zone sans métier explicite : id de catégorie (ex. restauration, sante_medical, high_ticket).",
    ),
    max_results: int = typer.Option(
        12,
        "--max",
        "-n",
        help="Mode ciblé : max domaines par recherche. Mode --zone : plafond global après déduplication.",
    ),
    max_per_metier: int = typer.Option(
        8,
        "--max-per-metier",
        help="Mode --zone uniquement : max domaines uniques par métier (chaque requête DuckDuckGo).",
    ),
    export: Optional[Path] = typer.Option(
        None,
        "--export",
        "-o",
        help="Fichier de sortie (.json ou .csv).",
    ),
    no_audit: bool = typer.Option(False, "--no-audit", help="Sourcing (et dédup zone) seuls, pas crawl / Groq."),
    force_audit: bool = typer.Option(
        False,
        "--force-audit",
        help="Lancer l'audit même si GEO_GROQ_API_KEY n'est pas défini (échouera côté API).",
    ),
    audit_all: bool = typer.Option(
        False,
        "--audit-all",
        help="Forcer un appel Groq sur chaque lead, même pastille verte (désactive le filtre coût).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Logs détaillés."),
) -> None:
    """Lance le sourcing, optionnellement crawl, audits Groq (filtre pastille par défaut)."""
    _setup_log(verbose)
    try:
        settings = Settings()
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Configuration:[/] {e}")
        raise typer.Exit(1) from e

    if not settings.has_groq() and not no_audit and not force_audit:
        console.print(
            "[yellow]GEO_GROQ_API_KEY est vide — lancez avec [bold]--no-audit[/] "
            "ou définissez la variable (fichier .env recommandé).[/]"
        )
        raise typer.Exit(1)

    zone_s = (zone or "").strip() or None
    metier_s = (metier or "").strip() or None
    ville_s = (ville or "").strip() or None

    if zone_s:
        city = zone_s
        if metier_s:
            metiers = [metier_s]
        else:
            key = (categorie or "").strip() or "high_ticket"
            try:
                _lbl, mlist = resolve_zone_metiers(key)
            except ValueError as e:
                console.print(f"[red]{e}[/]")
                raise typer.Exit(1) from e
            metiers = mlist
        zone_mode = True
        if ville_s and ville_s != city:
            console.print(
                "[red]Avec [bold]--zone[/], donnez la ville en valeur de l’option, "
                "sans second argument VILLE.[reset]"
            )
            raise typer.Exit(1)
    else:
        if not metier_s or not ville_s:
            console.print(
                "[red]Métier + ville requis, ou [bold]--zone VILLE[/] pour le mode multi-métiers.[/] "
                "Ex. [cyan]geo-stealth \"Menuisier\" \"Annecy\"[/] ou [cyan]geo-stealth --zone Annecy[/]."
            )
            raise typer.Exit(1)
        city = ville_s
        metiers = [metier_s]
        zone_mode = False

    async def pipeline() -> list[LeadRecord]:
        leads: list[LeadRecord] = []

        if zone_mode and len(metiers) > 0:
            nm = max(1, len(metiers))
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task_z = progress.add_task(
                    f"Recherche de [bold]{nm}[/] métiers sur {city}…",
                    total=nm,
                )
                leads = await zone_sourcing_multimetier(
                    city,
                    metiers,
                    settings,
                    max_per_metier=max(1, max_per_metier),
                    progress=progress,
                    task_id=task_z,
                )
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                t0 = progress.add_task("Sourcing DuckDuckGo…", total=None)
                hits = await search_leads_furtif(
                    metiers[0],
                    city,
                    settings,
                    max_results=max(1, max_results),
                )
                progress.update(
                    t0, completed=1, total=1, description="Sourcing terminé"
                )
            if not hits:
                console.print(
                    "[yellow]Aucun résultat (filtres stricts, ou moteur indisponible).[/]"
                )
            for h in hits:
                name = derive_company_name(h.url)
                leads.append(
                    LeadRecord(
                        company_name=name,
                        url=h.url,
                        metier=metiers[0],
                        city=city,
                        title=h.title,
                        source_rank=h.rank,
                    )
                )

        if not leads:
            return []

        n_raw = len(leads)
        leads = dedupe_leads_by_registered_domain(leads)
        n_dedup = len(leads)
        cap: int | None = None
        n_after = n_dedup
        if zone_mode:
            cap = max(1, max_results)
            if n_dedup > cap:
                leads = leads[:cap]
                n_after = len(leads)
        dedup_line = f"[dim]Déduplication :[/] [bold]{n_raw}[/] ➜ [bold]{n_dedup}[/] domaine(s) unique(s)"
        if zone_mode and cap is not None and n_after < n_dedup:
            dedup_line += f" → [bold]{n_after}[/] après [bold]-n {cap}[/] (plafond global)"
        console.print(dedup_line)

        if no_audit:
            return leads

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            t_c = progress.add_task("Crawl des pages d'accueil…", total=1)
            await crawl_leads_concurrent(leads, settings)
            progress.update(
                t_c,
                completed=1,
                total=1,
                description="Crawl terminé (preuves JSON-LD, title, H1)",
            )

        n_green = sum(1 for rec in leads if rec.crawl and rec.crawl.has_relevant_business_schema)
        n_sans_crawl = sum(1 for rec in leads if rec.crawl is None)
        if audit_all:
            n_to_groq = len(leads)
        else:
            n_to_groq = sum(
                1
                for rec in leads
                if not (rec.crawl and rec.crawl.has_relevant_business_schema)
            )
        sc_note = f" · [dim][{n_sans_crawl} sans crawl fiable][/]" if n_sans_crawl else ""
        console.print(
            f"\n[bold]Résumé avant IA[/] : [bold]{len(leads)}[/] lead(s) crawlé(s) · "
            f"[green]{n_green}[/] « optimisé » (schéma business déjà présent) · "
            f"[yellow]{n_to_groq}[/] envoi(s) vers Groq{sc_note}\n"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            t2 = progress.add_task(
                f"Audits Groq (≈{n_to_groq} appel(s))…",
                total=n_to_groq or 1,
            )
            res = await audit_leads_concurrent(
                leads,
                settings,
                cash_machine=not audit_all,
            )
            progress.update(
                t2,
                completed=n_to_groq or 1,
                total=n_to_groq or 1,
                description="Audits terminés",
            )
        return res

    try:
        rows = asyncio.run(pipeline())
    except Exception as e:  # noqa: BLE001
        LOG.exception("Arrêt faute d'erreur fatale")
        console.print(f"[red]Erreur fatale:[/] {e}")
        raise typer.Exit(2) from e

    if export is not None:
        suffix = export.suffix.lower()
        if suffix == ".json":
            export_json(export, rows)
        elif suffix in (".csv", ".tsv"):
            export_csv(export, rows)
        else:
            console.print("[red]Extension export non reconnue — utilisez .json ou .csv[/]")
            raise typer.Exit(1)
        console.print(f"Export écrit: [green]{export.resolve()}[/]")

    if rows:
        _print_results(rows, sourcing_only=no_audit, zone_mode=zone_mode)
    else:
        console.print("Aucune ligne à afficher.")


def main() -> None:
    """Point d'entrée console déclaré dans ``pyproject.toml``."""
    app()


if __name__ == "__main__":
    main()
