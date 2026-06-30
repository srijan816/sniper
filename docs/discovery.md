# Discovery (candidate sourcing)

Discovery finds **candidate listings** across the web; the SigLIP+DINOv2+pHash
ensemble (see `backend/app/services/vision.py`) makes the actual counterfeit
decision. So discovery only needs to supply plausible candidates — it does not
need to do visual matching itself.

## Sources (behind one `DiscoveryCandidate` seam)

`discover_candidates_for_asset()` in `services/discovery_orchestrator.py` merges:

1. **SerpApi** (`services/serpapi_service.py`) — Google Lens / Bing reverse-image /
   Google Shopping. **Optional**: runs only when `SERPAPI_KEY` is set. Paid.
2. **SearXNG** (`services/searxng_service.py`) — **free, self-hosted**. Runs when
   `discovery_enable_searxng=true`. Lanes:
   - image search (`categories=images`, `bing images`) → visual candidates,
   - marketplace `site:<host>` web search (Bing) across `discovery_marketplaces`.
3. **eBay Browse API** (`services/ebay_service.py`) — **free, official**. Runs when
   `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET` are set. Lanes: `searchByImage` (the
   protected photo → eBay's own visual match) + keyword search. eBay is a major
   counterfeit venue and pairs with eBay VeRO for takedowns.

All candidates are then verified by the ensemble, so a low-precision feed is fine.

## Counterfeits wall (admin-only)

`GET /api/counterfeits` (`app/api/counterfeits.py`) requires an **admin** bearer
token and returns only **human-reviewed** threats (status in APPROVED / CONFIRMED
/ TAKEDOWN_* / REMOVED) — never raw automated discoveries — each pairing the
original asset image with the infringing listing image + similarity. The page
lives at `/admin/counterfeits` (`src/app/admin/counterfeits/page.tsx`, behind the
auth middleware) and fetches with the signed-in admin's token, showing a
"suspected, automated, unverified" disclaimer. Empty until real reviewed matches
exist. It is intentionally **not public** — it exposes cross-client asset images
and enforcement actions.

## SearXNG reuse

We reuse the shared SearXNG from the app2 deep-research stack instead of running
our own. The SniperIP containers join the external docker network
`app2_deep_research_net` (see `docker-compose.prod.yml`) and reach it at
`SEARXNG_URL=http://searxng:8080`.

Config (`.env` / `app/core/config.py`):

| var | default | meaning |
|-----|---------|---------|
| `SEARXNG_URL` | `http://searxng:8080` | in-network SearXNG endpoint |
| `searxng_engines` | `bing` | web engines (Bing works without a proxy) |
| `searxng_image_engines` | `bing images` | image engines |
| `discovery_enable_searxng` | `true` | toggle the free lanes |
| `discovery_marketplaces` | `ebay.com,aliexpress.com,…` | `site:` targets |

### Engine notes (verified on this host)
- **Bing web + Bing images: work** (no proxy needed). This is the reliable feed.
- **Google / DuckDuckGo / Brave / Startpage: CAPTCHA/rate-limited** from a
  datacenter IP — need residential proxies to be useful.
- **eBay engine: "access denied"** (eBay blocks scraping) — use the official free
  **eBay Browse API** (`searchByImage` + keyword) instead; it doubles as the
  takedown channel via eBay VeRO.

## Reverse image (status)

True whole-web reverse-image (upload a photo → find where it appears) via
**Yandex / Google Lens is soft-blocked from this datacenter IP** (Yandex renders
but returns `SerpList_emptyPage` / "No matching results"; no CAPTCHA, just empty).
Making it work requires **residential proxies** (the stack already has ZenRows
proxy env wired) or a paid API (SerpApi Lens).

What we use instead, which is reliable and free: **keyword image search (SearXNG)
+ the ensemble**. Counterfeit sellers overwhelmingly **reuse the brand's exact
photo**, which the ensemble catches at ~1.0 (exact) / ~0.97 (edited), while
genuinely different photos of the same model score 0.5–0.8 and are not flagged.

## End-to-end test

`scripts`-free reproduction lives in the session scratchpad; the verified result:
discovery via SearXNG returned real Rolex listings; an exact-reuse photo scored
**1.000 (FLAGGED)**, an edited-reuse counterfeit **0.971 (FLAGGED)**, and
different-seller photos of the same model 0.57–0.80 (ignored).
