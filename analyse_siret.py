#!/usr/bin/env python3
"""
Analyse SIRET via l'API recherche-entreprises.api.gouv.fr
Saisir un ou plusieurs numéros de SIRET pour obtenir les informations de l'entreprise.
"""

import urllib.request
import urllib.error
import json
import sys
import time

API_URL = "https://recherche-entreprises.api.gouv.fr/search?q="

CAT_NIVEAU_1 = {
    "0": "Organisme de placement collectif en valeurs mobilières sans personnalité morale",
    "1": "Entrepreneur individuel",
    "2": "Groupement de droit privé non doté de la personnalité morale",
    "3": "Personne morale de droit étranger",
    "4": "Personne morale de droit public soumise au droit commercial",
    "5": "Société commerciale",
    "6": "Autre personne morale immatriculée au RCS",
    "7": "Personne morale et organisme soumis au droit administratif",
    "8": "Organisme privé spécialisé",
    "9": "Groupement de droit privé",
}

CAT_NIVEAU_2 = {
    "00": "Organisme de placement collectif en valeurs mobilières sans personnalité morale",
    "10": "Entrepreneur individuel",
    "21": "Indivision",
    "22": "Société créée de fait",
    "23": "Société en participation",
    "24": "Fiducie",
    "27": "Paroisse hors zone concordataire",
    "28": "Assujetti unique à la TVA",
    "29": "Autre groupement de droit privé non doté de la personnalité morale",
    "31": "Personne morale de droit étranger, immatriculée au RCS",
    "32": "Personne morale de droit étranger, non immatriculée au RCS",
    "41": "Établissement public ou régie à caractère industriel ou commercial",
    "51": "Société coopérative commerciale particulière",
    "52": "Société en nom collectif",
    "53": "Société en commandite",
    "54": "Société à responsabilité limitée (SARL)",
    "55": "Société anonyme à conseil d'administration",
    "56": "Société anonyme à directoire",
    "57": "Société par actions simplifiée",
    "58": "Société européenne",
    "61": "Caisse d'épargne et de prévoyance",
    "62": "Groupement d'intérêt économique",
    "63": "Société coopérative agricole",
    "64": "Société d'assurance mutuelle",
    "65": "Société civile",
    "69": "Autre personne morale de droit privé inscrite au RCS",
    "71": "Administration de l'état",
    "72": "Collectivité territoriale",
    "73": "Établissement public administratif",
    "74": "Autre personne morale de droit public administratif",
    "81": "Organisme gérant un régime de protection sociale à adhésion obligatoire",
    "82": "Organisme mutualiste",
    "83": "Comité d'entreprise",
    "84": "Organisme professionnel",
    "85": "Organisme de retraite à adhésion non obligatoire",
    "91": "Syndicat de propriétaires",
    "92": "Association loi 1901 ou assimilé",
    "93": "Fondation",
    "99": "Autre personne morale de droit privé",
}


def calculer_tva(siren: str) -> str:
    """Calcule le numéro de TVA intracommunautaire à partir du SIREN."""
    siren_int = int(siren)
    cle = (12 + 3 * (siren_int % 97)) % 97
    return f"FR{cle:02d}{siren}"


def appeler_api(siret: str, max_retries: int = 3) -> dict | None:
    """Appelle l'API avec retry sur erreur 429."""
    url = API_URL + siret
    req = urllib.request.Request(url, headers={"Accept": "application/json"})

    for tentative in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  ⏳ Rate limit atteint, pause 2s (tentative {tentative}/{max_retries})...")
                time.sleep(2)
            else:
                print(f"  ❌ Erreur HTTP {e.code}")
                return None
        except urllib.error.URLError as e:
            print(f"  ❌ Erreur réseau : {e.reason}")
            return None
    return None


def extraire_infos(data: dict, siret: str) -> dict | None:
    """Extrait les informations pertinentes du JSON retourné par l'API."""
    if data.get("total_results", 0) == 0:
        return None

    r = data["results"][0]
    siege = r.get("siege", {})
    siren = r.get("siren", siret[:9])
    nat_jur = r.get("nature_juridique", "")

    return {
        "SIRET": siret,
        "SIREN": siren,
        "Nom complet": r.get("nom_complet", ""),
        "Raison sociale": r.get("nom_raison_sociale", ""),
        "Adresse": siege.get("adresse", ""),
        "Code postal": siege.get("code_postal", ""),
        "Commune": siege.get("libelle_commune", ""),
        "Département": siege.get("departement", ""),
        "Nature juridique": nat_jur,
        "TVA intracom": calculer_tva(siren),
        "Cat. juridique niv.1": CAT_NIVEAU_1.get(str(nat_jur)[:1], ""),
        "Cat. juridique niv.2": CAT_NIVEAU_2.get(str(nat_jur)[:2], ""),
    }


def afficher_resultat(infos: dict):
    """Affiche les résultats de manière formatée."""
    largeur = max(len(k) for k in infos) + 2
    print()
    print("─" * 70)
    for cle, val in infos.items():
        print(f"  {cle:<{largeur}} │ {val}")
    print("─" * 70)


def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          ANALYSE SIRET - API Entreprises gouv.fr        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("Saisissez un numéro de SIRET (ou 'q' pour quitter).")
    print("Vous pouvez aussi saisir plusieurs SIRET séparés par des virgules.")
    print()

    while True:
        try:
            saisie = input("SIRET > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir !")
            break

        if saisie.lower() in ("q", "quit", "exit", ""):
            print("Au revoir !")
            break

        sirets = [s.strip().replace(" ", "") for s in saisie.split(",")]

        for i, siret in enumerate(sirets):
            if not siret.isdigit() or len(siret) != 14:
                print(f"  ⚠️  '{siret}' n'est pas un SIRET valide (14 chiffres attendus)")
                continue

            print(f"  🔍 Interrogation de l'API pour {siret}...")
            data = appeler_api(siret)

            if data is None:
                print(f"  ❌ Impossible de contacter l'API pour {siret}")
                continue

            infos = extraire_infos(data, siret)
            if infos is None:
                print(f"  ❌ SIRET {siret} non trouvé dans la base")
                continue

            afficher_resultat(infos)

            # Pause entre les appels si plusieurs SIRET (5 appels/sec)
            if i < len(sirets) - 1:
                time.sleep(0.2)

        print()


if __name__ == "__main__":
    main()
