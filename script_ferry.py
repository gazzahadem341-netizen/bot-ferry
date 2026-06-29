"""
script_ferry.py
Scrape directferries.fr pour Marseille → Tunis et envoie un bilan sur Discord.
Le webhook Discord est lu depuis la variable d'environnement DISCORD_WEBHOOK_URL.
"""

import os
import re
import requests
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright


# ─── Config ────────────────────────────────────────────────────────────────────

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# Dates : départ dans ~30 jours, retour dans ~45 jours (ajuste si besoin)
today        = datetime.today()
DATE_ALLER   = today + timedelta(days=30)
DATE_RETOUR  = today + timedelta(days=45)

# ─── Helpers ───────────────────────────────────────────────────────────────────

def extraire_prix(texte: str) -> int | None:
    """Extrait le premier entier trouvé dans une chaîne de type '1 234 €'."""
    chiffres = re.sub(r"\s", "", texte)          # supprime les espaces insécables
    match = re.search(r"\d+", chiffres)
    return int(match.group()) if match else None


def envoyer_discord(message: str) -> None:
    if not WEBHOOK_URL:
        print("⚠️  DISCORD_WEBHOOK_URL non défini — message non envoyé.")
        return
    resp = requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)
    if resp.status_code in (200, 204):
        print("✅ Message envoyé sur Discord.")
    else:
        print(f"❌ Erreur Discord {resp.status_code}: {resp.text}")


def selectionner_date_calendrier(page, date: datetime, test_id_prefix: str) -> None:
    """
    Clique sur le bon jour dans le widget calendrier de directferries.
    test_id_prefix : 'calendar-container-year-YYYY-month-M' (month 0-indexé)
    """
    annee  = date.year
    mois   = date.month - 1          # directferries utilise month 0-indexé
    jour   = str(date.day)
    tid    = f"calendar-container-year-{annee}-month-{mois}"
    page.get_by_test_id(tid).get_by_role("button", name=jour).click()


# ─── Scraping principal ────────────────────────────────────────────────────────

def scraper_ferry() -> list[dict]:
    resultats = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="fr-FR",
            geolocation={"latitude": 48.8566, "longitude": 2.3522},
            permissions=["geolocation"],
        )
        page = context.new_page()

        # ── 1. Accueil ──
        page.goto("https://www.directferries.fr/?culture=fr-FR", wait_until="domcontentloaded")

        # Cookies
        for label in ("Tout accepter", "Accept all"):
            try:
                page.get_by_role("button", name=label).click(timeout=4000)
                break
            except Exception:
                pass

        # ── 2. Sélection port départ (Marseille) ──
        page.get_by_role("button", name="De").click()
        page.get_by_test_id(
            "search-widget-outbound-popular-destination-port-result-FRMRS"
        ).click()

        # ── 3. Sélection port arrivée (Tunis) ──
        page.get_by_test_id("home-search-widget-return-popup-port-field-input").click()
        page.get_by_test_id(
            "search-widget-return-popular-destination-port-result-TUN"
        ).click()

        # ── 4. Dates dynamiques ──
        selectionner_date_calendrier(page, DATE_ALLER, "")
        selectionner_date_calendrier(page, DATE_RETOUR, "")
        page.get_by_test_id("search-widget-date-selector-footer-submit-button").click()

        # ── 5. Passagers : 2 adultes + 1 voiture ──
        adult_plus = page.get_by_test_id(
            "search-widget-quote-selector-popup-adult-container"
        ).get_by_test_id("counter-plus")
        adult_plus.click()   # passe de 1 → 2
        adult_plus.click()   # passe de 2 → 3  (retire cette ligne si tu veux 2 adultes)

        page.get_by_test_id("search-widget-quote-selector-vehicle-select-trigger").click()
        page.get_by_text("Voiture").click()
        page.locator("html").click()   # ferme le dropdown

        page.get_by_test_id("search-widget-quote-selector-popup-confirm").click()

        # ── 6. Lancement de la recherche (nouvelle popup) ──
        with page.expect_popup() as popup_info:
            page.get_by_role("button", name="search Rechercher").click()
        results_page = popup_info.value
        results_page.wait_for_load_state("domcontentloaded")

        # ── 7. Récupération de toutes les offres ──
        # Montre les routes masquées si présent
        try:
            results_page.get_by_test_id("results-hidden-routes-toggle").click(timeout=4000)
        except Exception:
            pass

        # Attendre que les prix soient chargés
        results_page.wait_for_selector(".price-value", timeout=15000)

        blocs = results_page.locator(".result-item, [data-testid*='result-card'], .ferry-result").all()

        if blocs:
            for bloc in blocs:
                try:
                    compagnie_el = bloc.locator("[class*='operator'], [class*='company'], [class*='name']").first
                    prix_el      = bloc.locator(".price-value").first
                    heure_el     = bloc.locator("[class*='departure'], [class*='time']").first

                    compagnie = compagnie_el.inner_text(timeout=2000).strip() if compagnie_el.count() else "N/A"
                    prix_txt  = prix_el.inner_text(timeout=2000).strip() if prix_el.count() else ""
                    heure     = heure_el.inner_text(timeout=2000).strip() if heure_el.count() else "N/A"
                    prix      = extraire_prix(prix_txt)

                    if prix:
                        resultats.append({
                            "compagnie": compagnie,
                            "heure":     heure,
                            "prix":      prix,
                        })
                except Exception:
                    continue
        else:
            # Fallback : on prend tous les .price-value visibles
            prix_els = results_page.locator(".price-value").all()
            for el in prix_els:
                try:
                    txt  = el.inner_text(timeout=2000).strip()
                    prix = extraire_prix(txt)
                    if prix:
                        resultats.append({"compagnie": "N/A", "heure": "N/A", "prix": prix})
                except Exception:
                    continue

        context.close()
        browser.close()

    # Tri par prix croissant
    resultats.sort(key=lambda x: x["prix"])
    return resultats


# ─── Formatage du message Discord ─────────────────────────────────────────────

def formater_message(resultats: list[dict]) -> str:
    date_aller  = DATE_ALLER.strftime("%d/%m/%Y")
    date_retour = DATE_RETOUR.strftime("%d/%m/%Y")
    now         = datetime.now().strftime("%d/%m/%Y à %H:%M")

    lignes = [
        "🚢 **Bilan Ferry — Marseille → Tunis**",
        f"📅 Aller : **{date_aller}** | Retour : **{date_retour}**",
        f"🕐 Mis à jour le {now}",
        "",
    ]

    if not resultats:
        lignes.append("❌ Aucune offre trouvée. Le site a peut-être changé sa structure.")
        return "\n".join(lignes)

    prix_liste = [r["prix"] for r in resultats]
    lignes += [
        f"📊 **{len(resultats)}** offre(s) trouvée(s)",
        f"💚 Meilleur prix : **{min(prix_liste)} €**",
        f"🔴 Prix max : **{max(prix_liste)} €**",
        f"🟡 Prix moyen : **{round(sum(prix_liste)/len(prix_liste))} €**",
        "",
        "─────────────────────────",
    ]

    for i, r in enumerate(resultats[:8], 1):   # max 8 résultats pour ne pas spammer
        ligne = f"**{i}.** {r['compagnie']} | 🕐 {r['heure']} | 💶 **{r['prix']} €**"
        lignes.append(ligne)

    lignes.append("\n🔗 https://www.directferries.fr")
    return "\n".join(lignes)


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"📅 Aller : {DATE_ALLER.strftime('%d/%m/%Y')} | Retour : {DATE_RETOUR.strftime('%d/%m/%Y')}")
    print("🔍 Scraping en cours...\n")

    try:
        resultats = scraper_ferry()
        print(f"✅ {len(resultats)} offres trouvées.")
        for r in resultats:
            print(f"  {r['compagnie']:25s} | {r['heure']} | {r['prix']} €")
    except Exception as e:
        print(f"❌ Erreur scraping : {e}")
        resultats = []

    message = formater_message(resultats)
    print(f"\n📨 Message Discord :\n{message}\n")
    envoyer_discord(message)
