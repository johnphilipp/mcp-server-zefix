"""Centralized localization labels for the Zefix MCP server.

All display strings use the official Zefix website terminology
(sourced from zefix.ch i18n translation files) in de/fr/it/en.

Internal constants (e.g. Company.status = "ACTIVE") remain English
for programmatic use. This module maps them to localized display
strings at formatting time.
"""

LABELS: dict[str, dict[str, str]] = {
    # Status display values
    "active": {
        "de": "aktiv",
        "fr": "active",
        "it": "attivo",
        "en": "active",
    },
    "deleted": {
        "de": "gelöscht",
        "fr": "radiée",
        "it": "cancellata",
        "en": "deleted",
    },
    # Structure table roles
    "head_office": {
        "de": "Hauptsitz",
        "fr": "Siège principal",
        "it": "Sede principale",
        "en": "Head office",
    },
    "branch": {
        "de": "Zweigniederlassung",
        "fr": "Succursale",
        "it": "Succursale",
        "en": "Branch",
    },
    "company_structure": {
        "de": "Firmenstruktur",
        "fr": "Structure de l'entreprise",
        "it": "Struttura aziendale",
        "en": "Company Structure",
    },
    "role": {
        "de": "Rolle",
        "fr": "Rôle",
        "it": "Ruolo",
        "en": "Role",
    },
    "address_seat": {
        "de": "Adresse / Sitz",
        "fr": "Adresse / Siège",
        "it": "Recapito / Sede",
        "en": "Address / Seat",
    },
    # Detail field labels
    "uid_label": {
        "de": "UID",
        "fr": "IDE",
        "it": "IDI",
        "en": "UID",
    },
    "chid_label": {
        "de": "CH-ID",
        "fr": "CH-ID",
        "it": "CH-ID",
        "en": "CH-ID",
    },
    "status_label": {
        "de": "Status",
        "fr": "Statut",
        "it": "Stato",
        "en": "Status",
    },
    "legal_form": {
        "de": "Rechtsform",
        "fr": "Forme juridique",
        "it": "Forma giuridica",
        "en": "Legal form",
    },
    "seat": {
        "de": "Sitz",
        "fr": "Siège",
        "it": "Sede",
        "en": "Seat",
    },
    "address": {
        "de": "Adresse",
        "fr": "Adresse",
        "it": "Recapito",
        "en": "Address",
    },
    "purpose": {
        "de": "Zweck",
        "fr": "But",
        "it": "Scopo",
        "en": "Purpose",
    },
    "capital": {
        "de": "Kapital",
        "fr": "Capital",
        "it": "Capitale",
        "en": "Capital",
    },
    "shab_date": {
        "de": "Letzte SHAB-Publ.",
        "fr": "Dernière publ. FOSC",
        "it": "Ultima pubbl. FUSC",
        "en": "Last SOGC publication",
    },
    "delete_date": {
        "de": "Löschungsdatum",
        "fr": "Date de radiation",
        "it": "Data di cancellazione",
        "en": "Deletion date",
    },
    "cantonal_excerpt": {
        "de": "Kantonaler Auszug",
        "fr": "Extrait cantonal",
        "it": "Estratto cantonale",
        "en": "Cantonal excerpt",
    },
    "audit_firms": {
        "de": "Revisionsstelle",
        "fr": "Organe de révision",
        "it": "Ufficio di revisione",
        "en": "Auditor",
    },
    "old_names": {
        "de": "Frühere Fassungen",
        "fr": "Versions précédentes",
        "it": "Versione precedente",
        "en": "Earlier versions",
    },
    "has_taken_over": {
        "de": "Hat übernommen",
        "fr": "A repris",
        "it": "Ha rilevato",
        "en": "Has taken over",
    },
    "taken_over_by": {
        "de": "Übernommen durch",
        "fr": "Repris par",
        "it": "Rilevata da",
        "en": "Taken over by",
    },
    "head_offices_label": {
        "de": "Hauptsitz",
        "fr": "Siège principal",
        "it": "Sede principale",
        "en": "Head office",
    },
    "branch_offices": {
        "de": "Zweigniederlassungen",
        "fr": "Succursales",
        "it": "Succursale",
        "en": "Branches",
    },
    # Section titles
    "shab_publications": {
        "de": "SHAB-Publikationen",
        "fr": "Publications FOSC",
        "it": "Pubblicazioni FUSC",
        "en": "SOGC Publications",
    },
    "legal_forms_title": {
        "de": "Rechtsformen",
        "fr": "Formes juridiques",
        "it": "Forme giuridiche",
        "en": "Legal Forms",
    },
    # Search results
    "results_for": {
        "de": "Ergebnis(se) für",
        "fr": "résultat(s) pour",
        "it": "risultato/i per",
        "en": "result(s) for",
    },
    "no_companies_found": {
        "de": "Keine Firmen gefunden für",
        "fr": "Aucune entreprise trouvée pour",
        "it": "Nessuna impresa trovata per",
        "en": "No companies found matching",
    },
    # Structure notices
    "cap_notice": {
        "de": (
            "Vollständige Adressen für die ersten {n}"
            " Zweigniederlassungen."
            " Übrige zeigen nur den Sitz."
        ),
        "fr": (
            "Adresses complètes pour les {n} premières"
            " succursales."
            " Les autres affichent uniquement le siège."
        ),
        "it": (
            "Indirizzi completi per le prime {n} succursali."
            " Le altre mostrano solo la sede."
        ),
        "en": (
            "Full addresses shown for the first {n} branches."
            " Remaining branches show registered seat only."
        ),
    },
    "no_structure": {
        "de": (
            "Keine Hauptsitze oder Zweigniederlassungen"
            " für diese Firma gefunden."
        ),
        "fr": (
            "Aucun siège principal ni succursale trouvé"
            " pour cette entreprise."
        ),
        "it": (
            "Nessuna sede principale né succursale trovata"
            " per questa impresa."
        ),
        "en": "No parent or branch offices found for this company.",
    },
    "name": {
        "de": "Firma",
        "fr": "Raison de commerce",
        "it": "Ditta",
        "en": "Name",
    },
}

_STATUS_DISPLAY: dict[str, str] = {
    "ACTIVE": "active",
    "DELETED": "deleted",
}


def label(key: str, lang: str) -> str:
    """Look up a localized label, falling back to English."""
    translations = LABELS.get(key, {})
    return translations.get(lang, translations.get("en", key))


def status_label(status: str, lang: str) -> str:
    """Map an internal status constant to a localized display string."""
    key = _STATUS_DISPLAY.get(status, "")
    if key:
        return label(key, lang)
    return status
