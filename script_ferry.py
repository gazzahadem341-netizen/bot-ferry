import re
import requests  # À mettre tout en haut du fichier avec tes autres imports
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.directferries.fr/")
    page.get_by_role("button", name="Tout accepter").click()
    page.get_by_role("button", name="De").click()
    page.get_by_test_id("search-widget-outbound-popular-destination-port-result-FRMRS").click()
    page.get_by_test_id("home-search-widget-return-popup-port-field-input").click()
    page.get_by_test_id("search-widget-return-popular-destination-port-result-TUN").click()
    page.get_by_test_id("calendar-container-year-2026-month-1").get_by_role("button", name="11").click()
    page.get_by_role("button", name="chevron-right").click()
    page.get_by_test_id("calendar-container-year-2026-month-1").get_by_role("button", name="22").click()
    page.get_by_test_id("calendar-container-year-2026-month-1").get_by_role("button", name="23").click()
    page.get_by_test_id("calendar-container-year-2026-month-0").get_by_role("button", name="11").click()
    page.get_by_test_id("calendar-container-year-2026-month-1").get_by_role("button", name="23").click()
    page.get_by_test_id("search-widget-date-selector-footer-submit-button").click()
    page.get_by_test_id("search-widget-quote-selector-popup-adult-container").get_by_test_id("counter-plus").click()
    page.get_by_test_id("search-widget-quote-selector-popup-adult-container").get_by_test_id("counter-plus").click()
    page.get_by_test_id("search-widget-quote-selector-vehicle-select-trigger").click()
    page.get_by_text("Voiture").click()
    page.get_by_test_id("search-widget-quote-selector-vehicle-select-trigger").click()
    page.locator("html").click()
    page.get_by_test_id("search-widget-quote-selector-vehicle-select-trigger").click()
    page.locator("html").click()
    page.get_by_test_id("search-widget-quote-selector-popup-confirm").click()
    with page.expect_popup() as page1_info:
        page.get_by_role("button", name="search Rechercher").click()
    page1 = page1_info.value
    page1.get_by_test_id("results-hidden-routes-toggle").click()
    page1.get_by_test_id("results-hidden-routes-toggle").click()
    page1.get_by_test_id("results-hidden-routes-toggle").click()
    page1.get_by_test_id("results-next-day-button-desktop").click()
    page1.get_by_test_id("results-hidden-routes-toggle").click()
    page1.get_by_test_id("results-heading-shift-date-left").click()
    page1.get_by_test_id("results-heading-shift-date-left").click()
    page1.get_by_test_id("results-hidden-routes-toggle").click()
    page1.get_by_test_id("results-hidden-routes-toggle").click()
    page1.get_by_role("button", name="ven. 10 juil.").click()
    page1.get_by_test_id("calendar-container-year-2026-month-0").get_by_role("button", name="13").click()
    page1.get_by_test_id("calendar-container-year-2026-month-1").get_by_role("button", name="24").click()
    page1.get_by_test_id("search-widget-date-selector-footer-submit-button").click()
    page1.get_by_test_id("results-hidden-routes-toggle").click()
    page1.get_by_role("button", name="lun. 13 juil.").click()
    page1.get_by_test_id("calendar-container-year-2026-month-0").get_by_role("button", name="12").click()
    page1.get_by_test_id("calendar-container-year-2026-month-1").get_by_role("button", name="23").click()
    page1.get_by_test_id("search-widget-date-selector-footer-submit-button").click()
    page1.get_by_test_id("results-hidden-routes-toggle").click()
    page1.get_by_test_id("results-heading-shift-date-left").click()
    page1.get_by_test_id("results-hidden-routes-toggle").click()

    texte_du_prix = page1.locator(".price-value").first.inner_text()
    prix_chiffre = int(''.join(filter(str.isdigit, texte_du_prix)))
    
    URL_WEBHOOK_DISCORD = "https://discord.com/api/webhooks/1521130897850503341/VMb9UhsWzikLUoXet2riHodMpTVA44XYhXWF35IpwNGJ5XF1g4c-1ZcFJRC1qxRSRctJ"

    bilan_message = f"🚢 **Bilan Ferry France - Tunis** 🚢\n\nUn départ a été analysé ! Le prix actuel trouvé est de **{prix_chiffre} €**."

    donnees = {
        "content": bilan_message
}

    requests.post(URL_WEBHOOK_DISCORD, json=donnees)

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
