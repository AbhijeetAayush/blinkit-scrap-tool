# Blinkit Brand Shelf Intelligence

Track **your SKUs and brand competitors** on Blinkit (price, stock, rank, ads, OOS). This is not a platform-vs-platform monitor (Blinkit vs Zepto). Coverage is unbounded: every pincode and SKU is a database row. There is no hardcoded pin or SKU list in workers.

v1 scrapes **Blinkit public pages** through unlockers. Empty HTML with no product cards raises `ParseEmptyError` and **does not** insert fake OOS rows.

## Accounts

Create these before deploy:

- AWS account, region **ap-south-1**, SAM CLI, Python 3.12
- [Supabase](https://supabase.com) project (Auth + Postgres)
- [Upstash](https://upstash.com) Redis + QStash
- [ZenRows](https://www.zenrows.com) and [ScrapingBee](https://www.scrapingbee.com) API keys
- Vercel (or any Next.js host) for `apps/web`

No AWS Secrets Manager or SSM. Secrets are CloudFormation Parameters entered at `sam deploy --guided` (`NoEcho`) and mapped to Lambda environment variables.

## Database

```bash
supabase db push
```

Optional demo rows (skip for a blank tenant):

```bash
psql "$DATABASE_URL" -f supabase/seed.sql
```

`seed.sql` is **optional demo data**. Workers never import it. Demo pins are `000001`–`000003`, not live catchments.

Realtime: `observations` and `alerts` are added to `supabase_realtime`.

## Workers (SAM)

From `infra/sam`:

```bash
sam build
sam deploy --guided
```

Guided prompts (paste values; they are not stored in git):

| Parameter | Notes |
| --- | --- |
| Stack Name | `blinkit-shelf-dev` |
| AWS Region | `ap-south-1` |
| SupabaseUrl / SupabaseServiceRoleKey | service role, never `NEXT_PUBLIC_` |
| ZenRowsApiKey / ScrapingBeeApiKey | unlockers |
| UpstashRedisUrl / UpstashRedisToken | REST URL + token |
| QstashToken / Current / Next signing keys | QStash console |
| UnlockerSearch | default `zenrows` |
| UnlockerLocation | default `scrapingbee` |
| DailyCreditBudget | default `400` |
| Confirm changeset | Y |
| **Allow Function URL without auth** | **Y** (QStash verifies JWT) |
| Save arguments to samconfig.toml | optional; file is **gitignored** |

Outputs: `DispatchUrl`, `ScrapeStoreUrl`, `DeriveUrl`, `ResolveStoresUrl`, `DataBucketName`.

`infra/sam/samconfig.example.toml` has no secrets. If guided writes `samconfig.toml` with parameter overrides, keep it gitignored.

Local invoke skeleton: copy `infra/sam/env.json.example` → `env.json` (gitignored).

## QStash schedules

After deploy, register IST crons (run once; the QStash schedules API is not fully idempotent by name):

```bash
set QSTASH_TOKEN=...
python infra/qstash/register.py --dispatch-url https://YOUR_DISPATCH.lambda-url.REGION.on.aws/ --resolve-url https://YOUR_RESOLVE.lambda-url.REGION.on.aws/
```

Schedules:

- Dispatch `0 9 * * *` body `{"slot_kind":"morning"}` → observed slot **today 09:00 Asia/Kolkata**
- Dispatch `0 19 * * *` body `{"slot_kind":"evening"}` → **today 19:00 IST**
- Resolve stores `0 6 * * *` → slot **06:00 IST** that calendar date

Confirm timezone **Asia/Kolkata** on the QStash schedule if the API does not honor TZ in cron.

**Manual Run now** publishes `{"slot_kind":"manual"}`. Slot pick: before 09:00 IST → today 09:00; before 19:00 → today 19:00; else next calendar day 09:00. Dispatch stamps one `observed_slot` on every scrape job in that run.

Unsigned POSTs to Function URLs return **401**.

## Web (Vercel)

Root directory: `apps/web`.

Public env:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Server-only (never `NEXT_PUBLIC_`):

- `QSTASH_TOKEN`
- `DISPATCH_URL` (stack output `DispatchUrl`)

Do not put service role, unlocker keys, or QStash signing keys in the browser.

```bash
cd apps/web
npm install
npm run dev
```

Onboarding creates a brand + `brand_members` owner. SKUs and coverage have **no max row count**. Pagination is 50.

### Adding 200 pincodes

Use **Coverage** in the UI (or insert into `pincodes`). Workers page with `PIN_PAGE_SIZE` (default 500) and continue until the table is exhausted. A fourth pin is not a code change.

Optional lat/lon helper: `data/in_pincode_lookup.example.json` (copied to `apps/web/public/` for the form). It is a dictionary, not the scrape universe.

## Credit budget

`DAILY_CREDIT_BUDGET` (UTC day, Redis `credits:day:{YYYY-MM-DD}`). When remaining ≤ 0, Dispatch writes a `credit_budget` alert and returns without enqueueing more stores.

## Tests

```bash
cd services/workers
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

## Legal

You are responsible for Blinkit Terms of Use, unlocker terms, and Indian DPDP obligations for any personal data in Auth. This repo fetches **public product listing pages** via third-party unlockers; it does not document or call unofficial private APIs. Respect robots/ToS, rate limits, and credit budgets. Do not store warehouse quantities — `inventory_shown` is UI-displayed stock only.

## Layout

- `apps/web` — Next.js 15 App Router
- `services/workers` — Python 3.12 Lambdas
- `infra/sam/template.yaml` — four Function URLs, S3 bronze/silver bucket
- `supabase/migrations/0001_init.sql` — RLS, `latest_observations`
