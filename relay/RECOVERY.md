# Relay recovery — `redline-sync`

The 🔄 Sync button in the app POSTs to a tiny HTTP relay; the relay calls GitHub's `workflow_dispatch` on `.github/workflows/sync.yml` with an Actions-only token. The app's one pointer to the relay is the **`SYNC_URL`** constant in `build/tail.html`. The source in this folder holds no secret — only env-var and secret *names*.

**Live since 2026-11-13 (app v867, commit `c18184e`): the Cloudflare Worker** `https://redline-sync.jgrimaldi.workers.dev`. The Val Town val it replaced, and that val's token, were deleted the same day (§5, §6).

| File | What it is | SHA-256 |
|---|---|---|
| `relay/worker.ts` | the **live relay**: Cloudflare Worker — dispatch plus a device key (`X-Sync-Key` header) and a cap of 9 dispatches per UTC day with 3 minutes between them (3,368 bytes). The deployed code is this file with the TypeScript annotations stripped; behaviour identical. | `b85bdb1e2a03cd51f4c1ff9e19b5fd2d28cf468622312716d4861984526f57d8` |
| `relay/main.ts` | historical: verbatim mirror of the **Val Town val** `joegrimaldi/redline-sync` as it ran 2026-09-20 → 2026-11-13; the val itself is deleted (1,129 bytes, 32 lines, no trailing newline) | `2d755cbfd3683fa9bac2fd835c821320d066d8272d9da063ce1dc72392984973` |

## 1. The Worker

**Bindings** (Worker → Settings): secret **`GH_TOKEN`** = the `redline-sync-cloudflare` token (§2); secret **`SYNC_KEY`** = the device key — a random 24-character alphanumeric string kept only in the password manager, the Worker secret and the phone; KV namespace binding **`SYNC_KV`** → namespace `redline-sync` (per-day counter + last-dispatch time). CORS is limited to `https://joegrimaldi.github.io`.

**Behaviour**: `OPTIONS` → 204 · not `POST` → 405 · wrong or missing `X-Sync-Key` → 401 · more than 9 dispatches in a UTC day, or one within 180 s of the last → 429 with the reason in the body · GitHub refuses → **502** `GitHub <status>: <message>` · success → 200 `Sync started`. Tested on deploy: 405 / 401 / 401 (wrong key) / 200 / 429.

**App side** (`build/tail.html`): the key is entered once per device through a `prompt()`, kept in `localStorage` under `syncKey`, sent as `X-Sync-Key`. On 401 the app forgets the key and asks again on the next tap; 429 and 502 texts are shown as toasts. Only the header name is in the source. The Update button clears caches and the service worker but not `localStorage`, so the key survives updates. Free plan limits (100k requests/day, 1k KV writes/day) are far above the cap.

**Recreate from scratch**: dash.cloudflare.com → Workers & Pages → Create → Worker named `redline-sync` → Edit code → paste `relay/worker.ts` (strip the type annotations if the editor is set to JavaScript) → Deploy; Storage & Databases → KV → create `redline-sync`; Worker → Settings → Bindings → add KV `SYNC_KV`; Settings → Variables and Secrets → add secrets `GH_TOKEN`, `SYNC_KEY`; Deploy. If the URL changes, update `SYNC_URL` in `build/tail.html` and push.

**Test** (Terminal): `curl -i <url>` → 405; `curl -i -X POST <url>` → 401; `curl -i -X POST -H "X-Sync-Key: <key>" <url>` → `Sync started` and a `workflow_dispatch` run in the Actions tab; a second POST within 3 min → 429.

## 2. The relay token

- Name: **`redline-sync-cloudflare`** (created 2026-11-13) — a fine-grained personal access token. Repository access: **only `joegrimaldi/redline`**. Permissions: **Actions: Read and write** (Metadata: read is implied). **Nothing else — never Contents: write.** The device key is the lock on the endpoint; the token must only be able to start a sync, never change the repo.
- Rotation: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → `redline-sync-cloudflare` → **Regenerate** → Worker → Settings → Variables and Secrets → edit `GH_TOKEN` → Deploy → run the §1 test. 🔄 is broken from the moment of regeneration until the secret is updated.
- Check the expiry date whenever you are in there; an expired token makes 🔄 report `GitHub 401`.
- The previous token **`redline-sync-relay`** (used by the val) was deleted on 2026-11-13. It was never given to the Worker.

## 3. Manual fallback (relay down, token expired, host gone)

GitHub → `joegrimaldi/redline` → **Actions** → *Redline Strava Sync* → **Run workflow** → branch `main`. This is exactly what the relay does. A push to anything under `build/**` also runs it.

## 4. Other credentials (names only)

- **`redline-local-push`** — fine-grained PAT, `joegrimaldi/redline` only, **Contents: read/write**. Used only for git pushes; lives in `.git/.credentials` (helper `store --file=.git/.credentials`, relative path) and the macOS keychain. Regenerating it stales both copies. It has no `workflow` scope, so `.github/workflows/*` can only be changed through the GitHub UI or a token that has it.
- Repo secrets read by `sync.yml` (Settings → Secrets and variables → Actions): **`STRAVA_CLIENT_ID`**, **`STRAVA_CLIENT_SECRET`**, **`STRAVA_REFRESH_TOKEN`**. If Strava auth fails in the workflow log, re-authorize the app in Strava's API settings, obtain a fresh refresh token and update the secret.

## 5. History: the Val Town val (deleted 2026-11-13)

The relay ran as the Val Town val `joegrimaldi/redline-sync` from 2026-09-20 to 2026-11-13: it answered any POST without a key, read `GH_TOKEN` from its per-val environment variables (the `redline-sync-relay` token) and had no cap. Val Town is winding down (read-only from 2026-12-10, all services end 2027-01-10 — blog.val.town/winding-down), so the val was deleted after the Worker took over. `relay/main.ts` keeps its source for the record; do not redeploy it.

## 6. Cutover record

All on 2026-11-13: Worker deployed and tested by hand with the new token → `c18184e` switched `SYNC_URL`, added the key prompt and removed the dead handler → v867 live, Worker answers the app's origin correctly (a keyless POST from the page gets a readable 401) → phone sync through the Worker verified at 01:49 UTC → token `redline-sync-relay` deleted on GitHub → val `redline-sync` deleted on Val Town. There is no relay to roll back to; if the Worker is down, §3 is the fallback and §1 recreates it.

## 7. Verify the mirrors

`shasum -a 256 relay/main.ts relay/worker.ts` must match the table above. Whenever the live relay code changes, update `worker.ts`, the hash and this section in the same commit.
