from __future__ import annotations

from playwright.async_api import Locator
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from .base import BaseJobScraper, JobOffer


class ApecScraper(BaseJobScraper):
    name = "apec"
    default_url = (
        "https://www.apec.fr/candidat/recherche-emploi.html/emploi?"
        "typesConvention=143684&typesConvention=143685&typesConvention=143686&typesConvention=143687"
        "&at_medium=sl&at_campaign=marque&at_platform=google&at_creation=marque_candidat"
        "&at_variant=&at_network=&at_term=apec%20offre%20d%20emploi&gclsrc=aw.ds&gad_source=1"
        "&gad_campaignid=7976498296&gbraid=0AAAAAD_P-vbpYbar1CMrXnwT2baZz9a0K"
        "&gclid=Cj0KCQiAubrJBhCbARIsAHIdxD-ZZBBupvlv0F81Yq1DSYwD14UVKem_1TjucNs-n7YX-_WYJnhS0ocaAnP_EALw_wcB"
        "&fonctions=101807&lieux=720"
    )

    def __init__(self, url: str | None = None, save_raw: bool = False, raw_dir: str = "outputs/raw"):
        self.url = url or self.default_url
        self.save_raw = save_raw
        self.raw_dir = raw_dir

    async def _first_text(self, locators: list[Locator]) -> str | None:
        for locator in locators:
            try:
                if await locator.count() == 0:
                    continue
                text = (await locator.first.inner_text()).strip()
                if text:
                    return text
            except Exception:
                continue
        return None

    async def _accept_cookie_banner(self, page) -> bool:
        selectors = [
            "button:has-text('Tout accepter')",
            "button:has-text('Accepter')",
            "button:has-text('J’accepte')",
            "button:has-text('J\'accepte')",
            "#didomi-notice-agree-button",
            "button[id*='agree']",
            "button[aria-label*='accepter' i]",
        ]

        for selector in selectors:
            button = page.locator(selector).first
            try:
                if await button.is_visible(timeout=2500):
                    await button.click()
                    await page.wait_for_timeout(500)
                    return True
            except PlaywrightTimeoutError:
                continue
            except Exception:
                continue

        for name in ["Tout accepter", "Accepter", "J’accepte", "J'accepte"]:
            try:
                role_button = page.get_by_role("button", name=name).first
                if await role_button.is_visible(timeout=1500):
                    await role_button.click()
                    await page.wait_for_timeout(500)
                    return True
            except Exception:
                continue

        return False

    async def _extract_job_links(self, results_page, max_results: int) -> list[tuple[str, str]]:
        anchors = results_page.locator("a[href*='/emploi/detail-offre/']")
        try:
            await anchors.first.wait_for(timeout=15000)
        except PlaywrightTimeoutError:
            anchors = results_page.locator("a[data-cy*='job-title'], a:has(h2), a:has(h3)")

        count = await anchors.count()
        links: list[tuple[str, str]] = []
        seen_urls: set[str] = set()

        for idx in range(count):
            if len(links) >= max_results:
                break

            anchor = anchors.nth(idx)
            href = await anchor.get_attribute("href")
            if not href:
                continue

            full_url = href if href.startswith("http") else f"https://www.apec.fr{href}"
            if full_url in seen_urls:
                continue

            short_title = await self._first_text(
                [
                    anchor.locator("h2"),
                    anchor.locator("h3"),
                    anchor.locator("[data-cy*='title']"),
                ]
            )
            if not short_title:
                short_title = ((await anchor.inner_text()) or "").strip().split("\n")[0]
            if not short_title:
                short_title = "Offre sans titre"

            seen_urls.add(full_url)
            links.append((short_title, full_url))

        return links

    async def _scrape_offer_details(self, offer_page, fallback_title: str, offer_url: str, raw_index: int) -> JobOffer:
        response = await offer_page.goto(offer_url, wait_until="domcontentloaded", timeout=90000)
        await offer_page.wait_for_timeout(800)

        if self.save_raw and response is not None:
            content = await offer_page.content()
            with open(f"{self.raw_dir}/apec_offer_{raw_index:03d}.html", "w", encoding="utf-8") as f:
                f.write(content)

        title = await self._first_text([offer_page.locator("h1[data-cy='job-title']"), offer_page.locator("main h1"), offer_page.locator("h1")])
        company = await offer_page.locator("apec-offre-metadata ul.details-offer-list li").first.inner_text()
        location = await offer_page.locator(
            "apec-offre-metadata ul.details-offer-list li"
        ).nth(2).inner_text()
        contract_type = await offer_page.locator(
            "apec-offre-metadata ul.details-offer-list li"
        ).nth(1).inner_text()
        salary = await offer_page.locator(
            "apec-poste-informations .details-post:has(h4:text('Salaire')) span"
        ).inner_text()
        publication_date = await offer_page.locator(
            "apec-offre-metadata .date-offre:has-text('Publiée')"
        ).inner_text()

        description = await offer_page.locator("apec-poste-informations").inner_text()

        if description:
            description = "\n".join(line.strip() for line in description.splitlines() if line.strip())

        return JobOffer(
            title=title or fallback_title,
            url=offer_url,
            company=company,
            location=location,
            contract_type=contract_type,
            salary=salary,
            publication_date=publication_date,
            description=description,
        )

    async def scrape_jobs(self, max_results: int = 20, headless: bool = True) -> list[JobOffer]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(locale="fr-FR")

            results_page = await context.new_page()
            await results_page.goto(self.url, wait_until="domcontentloaded", timeout=90000)
            await self._accept_cookie_banner(results_page)
            await results_page.wait_for_timeout(1500)

            links = await self._extract_job_links(results_page, max_results=max_results)

            offer_page = await context.new_page()
            offers: list[JobOffer] = []

            for idx, (fallback_title, offer_url) in enumerate(links, start=1):
                try:
                    details = await self._scrape_offer_details(offer_page, fallback_title, offer_url, raw_index=idx)
                    offers.append(details)
                except Exception:
                    offers.append(
                        JobOffer(
                            title=fallback_title,
                            url=offer_url,
                            company=None,
                            location=None,
                            contract_type=None,
                            salary=None,
                            publication_date=None,
                            description=None,
                        )
                    )

            await offer_page.close()
            await results_page.close()
            await context.close()
            await browser.close()
            return offers
