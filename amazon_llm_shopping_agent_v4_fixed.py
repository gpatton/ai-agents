import asyncio
import json
import os
import re
import sys
import time
import urllib.parse

from openai import OpenAI
from playwright.async_api import async_playwright

OPENAI_MODEL = "gpt-5.6-luna"
DEFAULT_GOAL = (
    "Build me a complete anti-aging skincare routine for under €100. "
    "Avoid unnecessary duplication, prioritise evidence-backed skincare, "
    "and choose products available on Amazon.ie."
)
CANDIDATES_PER_ITEM = 5

client = OpenAI()


def clean_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def ask_llm_for_plan(goal):
    prompt = f"""
You are the planning component of an Amazon.ie shopping agent.

User goal:
{goal}

Turn the goal into a sensible shopping plan. For skincare, favour evidence-backed
topical categories such as broad-spectrum sunscreen, retinoids/retinol,
moisturiser, and useful complementary products when appropriate.

Rules:
- Respect the user's total budget.
- Avoid unnecessary ingredient/product duplication.
- Do not diagnose conditions.
- Do not recommend prescription-only medicines.
- Keep the routine practical rather than adding products just to spend the budget.
- Give each planned item a maximum budget so the total of max_price_eur does not
  exceed the user's total budget.
- Produce precise Amazon.ie search queries.
- Return ONLY valid JSON.

Schema:
{{
  "goal_summary": "short summary",
  "budget_eur": 100,
  "items": [
    {{
      "category": "category",
      "search_query": "Amazon.ie search query",
      "purpose": "short reason",
      "max_price_eur": 25
    }}
  ]
}}
"""
    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[{"role": "user", "content": prompt}],
    )
    return clean_json(response.output_text)


def parse_euro_price(text):
    if not text:
        return None
    cleaned = text.replace("\xa0", " ").replace(",", ".")
    match = re.search(r"€\s*(\d+(?:\.\d{1,2})?)", cleaned)
    if not match:
        match = re.search(r"(\d+(?:\.\d{1,2})?)\s*€", cleaned)
    return float(match.group(1)) if match else None


async def handle_captcha(page):
    try:
        captcha = page.locator("input[placeholder='Type characters']")
        if "captcha" in page.url.lower() or await captcha.is_visible(timeout=1000):
            print("\n[Action Required] Amazon displayed a CAPTCHA.")
            print("Solve it manually in the browser; the agent will wait.")
            for _ in range(180):
                await page.wait_for_timeout(1000)
                if not await captcha.is_visible():
                    print("[Agent] CAPTCHA cleared.")
                    return
    except Exception:
        pass


async def find_amazon_candidates(page, search_query, limit=CANDIDATES_PER_ITEM):
    encoded = urllib.parse.quote_plus(search_query)
    url = f"https://www.amazon.ie/s?k={encoded}&fresh={int(time.time())}"

    print(f"\n[Browser] Searching: {search_query}")
    await page.goto(url, wait_until="domcontentloaded")
    await handle_captcha(page)
    await page.wait_for_timeout(1800)

    results = page.locator('[data-component-type="s-search-result"]')
    count = await results.count()
    candidates = []
    seen_urls = set()

    for i in range(min(count, 24)):
        if len(candidates) >= limit:
            break

        result = results.nth(i)
        link = result.locator('a[href*="/dp/"]').first
        if not await link.count():
            continue

        href = await link.get_attribute("href")
        if not href:
            continue

        product_url = href if href.startswith("http") else "https://www.amazon.ie" + href
        product_url = product_url.split("/ref=")[0]

        if product_url in seen_urls:
            continue
        seen_urls.add(product_url)

        try:
            title = (await result.locator("h2").first.inner_text()).strip()
        except Exception:
            title = "Amazon result"

        price_text = "Price not detected"
        try:
            price_loc = result.locator("span.a-price span.a-offscreen").first
            if await price_loc.count():
                price_text = (await price_loc.inner_text()).strip()
        except Exception:
            pass

        rating = "Rating not detected"
        try:
            rating_loc = result.locator("span.a-icon-alt").first
            if await rating_loc.count():
                rating = (await rating_loc.inner_text()).strip()
        except Exception:
            pass

        candidates.append(
            {
                "title": title,
                "url": product_url,
                "price": price_text,
                "price_eur": parse_euro_price(price_text),
                "rating": rating,
            }
        )

    return candidates


def choose_candidate_with_llm(item, candidates, remaining_budget):
    if not candidates:
        return None, "No Amazon candidates found."

    compact = [
        {
            "index": i,
            "title": c["title"],
            "price": c["price"],
            "price_eur": c["price_eur"],
            "rating": c["rating"],
        }
        for i, c in enumerate(candidates)
    ]

    prompt = f"""
You are the selection component of an Amazon.ie shopping agent.

Planned item:
{json.dumps(item, ensure_ascii=False)}

Remaining total budget: €{remaining_budget:.2f}

Real Amazon.ie candidates:
{json.dumps(compact, ensure_ascii=False, indent=2)}

Choose the best candidate using ONLY supplied information.

Rules:
- Strong title/search relevance is essential.
- Stay at or below both the item's max_price_eur and the remaining total budget
  whenever a usable numeric price is available.
- Consider the displayed rating after relevance and budget.
- Do not invent ingredients, sizes, ratings, prices, reviews, or properties.
- If none is a sufficiently relevant and budget-compatible choice, return
  selected_index as null.

Return ONLY JSON:
{{
  "selected_index": 0,
  "reason": "short explanation based only on supplied data"
}}
"""
    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[{"role": "user", "content": prompt}],
    )
    decision = clean_json(response.output_text)
    idx = decision.get("selected_index")

    if idx is None:
        return None, decision.get("reason", "No suitable candidate.")

    idx = int(idx)
    if idx < 0 or idx >= len(candidates):
        raise ValueError(f"LLM returned invalid candidate index: {idx}")

    return candidates[idx], decision.get("reason", "")


async def add_candidate_to_basket(page, candidate):
    if not candidate:
        return False

    print(f"[Basket] Opening: {candidate['title']}")
    await page.goto(candidate["url"], wait_until="domcontentloaded")
    await handle_captcha(page)
    await page.wait_for_timeout(1800)

    selectors = [
        "#add-to-cart-button",
        "#add-to-cart-button-ubb",
        'input[name="submit.add-to-cart"]',
        'span#submit.add-to-cart input',
    ]

    for selector in selectors:
        try:
            button = page.locator(selector).first
            if await button.is_visible(timeout=2500):
                await button.scroll_into_view_if_needed()
                await button.click()
                await page.wait_for_timeout(2200)
                print("[Basket] Added successfully.")
                return True
        except Exception:
            continue

    print("[Basket] No usable Add to Basket button found.")
    return False


async def run_agent():
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.")
        sys.exit(1)

    print("\n=== Amazon.ie LLM Shopping Agent ===")
    entered = input(
        "\nTell me what you want the agent to buy\n"
        f"(press Enter for the default goal):\n> "
    ).strip()
    goal = entered or DEFAULT_GOAL

    print(f"\n[Goal] {goal}")
    print("[LLM] Building a shopping plan...")
    plan = ask_llm_for_plan(goal)

    budget = float(plan.get("budget_eur", 100))
    items = plan.get("items", [])
    spent = 0.0

    print(f"\n[Plan] {plan.get('goal_summary', goal)}")
    print(f"[Budget] €{budget:.2f}")

    for i, item in enumerate(items, 1):
        print(
            f"{i}. {item['category']} — up to €{float(item['max_price_eur']):.2f}\n"
            f"   {item['purpose']}\n"
            f"   Search: {item['search_query']}"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 850})
        page = await context.new_page()

        await page.goto("https://www.amazon.ie", wait_until="domcontentloaded")
        await handle_captcha(page)

        try:
            cookie = page.locator("#sp-cc-accept")
            if await cookie.is_visible(timeout=2000):
                await cookie.click()
        except Exception:
            pass

        results_log = []

        for item in items:
            remaining = max(0.0, budget - spent)
            if remaining <= 0:
                print("\n[Budget] Total budget reached; stopping.")
                break

            try:
                candidates = await find_amazon_candidates(page, item["search_query"])
                print(f"[Agent] Found {len(candidates)} candidates.")

                candidate, reason = choose_candidate_with_llm(item, candidates, remaining)

                entry = {
                    "planned_item": item,
                    "amazon_candidates": candidates,
                    "selected_candidate": candidate,
                    "selection_reason": reason,
                    "remaining_budget_before": remaining,
                }

                if not candidate:
                    print(f"[LLM] Skipping {item['category']}: {reason}")
                    entry["added_to_basket"] = False
                    results_log.append(entry)
                    continue

                price = candidate.get("price_eur")
                max_item = float(item["max_price_eur"])

                # Hard Python guardrail: don't rely on the LLM alone for arithmetic.
                if price is not None and (price > remaining or price > max_item):
                    print(
                        f"[Budget Guard] Skipping {candidate['title']} at €{price:.2f}; "
                        "it exceeds the allowed budget."
                    )
                    entry["added_to_basket"] = False
                    entry["budget_guard_rejected"] = True
                    results_log.append(entry)
                    continue

                print("\n[LLM Selection]")
                print("Category:", item["category"])
                print("Selected:", candidate["title"])
                print("Price:", candidate["price"])
                print("Rating:", candidate["rating"])
                print("Reason:", reason)

                added = await add_candidate_to_basket(page, candidate)
                entry["added_to_basket"] = added

                if added and price is not None:
                    spent += price
                    print(f"[Budget] Running total: €{spent:.2f} / €{budget:.2f}")
                elif added:
                    print("[Budget] Item added, but Amazon price could not be parsed.")

                results_log.append(entry)

            except Exception as exc:
                print(f"[Agent] Error processing {item.get('category', 'item')}: {exc}")

        with open("shopping_agent_results.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "goal": goal,
                    "plan": plan,
                    "known_price_total_eur": round(spent, 2),
                    "results": results_log,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        print(f"\n[Agent] Finished. Known-price total: €{spent:.2f} / €{budget:.2f}")
        print("[Agent] Opening your basket for review.")
        await page.goto(
            "https://www.amazon.ie/gp/cart/view.html",
            wait_until="domcontentloaded",
        )
        await page.wait_for_timeout(2000)
        print("Review the basket yourself before purchasing.")
        print("Press Ctrl+C in the terminal to stop the agent.")

        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            pass
        finally:
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\n[Agent] Session closed.")
