"""Exceptions partagées du pipeline de prospection."""


class JobCancelled(Exception):
    """L'utilisateur a demandé l'arrêt (CRM / CLI). Le pipeline s'interrompt proprement."""
