# Relay recovery — `redline-sync`

The 🔄 Sync button in the app POSTs to a tiny HTTP relay; the relay calls GitHub's `workflow_dispatch` on `.github/workflows/sync.yml` with an Actions-only token. The app's one pointer to the relay is the **`SYNC_URL`** constant in `build/tail.html`. The source in this folder holds no secret — only env-var and secret *names*.

| File | What it is | SHA-256 |
|---|---|---|
| `relay/main.ts` | verbatim mirror of the **live Val Town val** `joegrimaldi/redline-sync` (captured 2026-11-12; 1,129 bytes, 32 lines, no trailing newline) | `2d755cbfd3683fa9bac2fd835c821320d066d8272d9da063ce1dc72392984973` |
| `relay/worker.ts` | the **Cloudflare Worker** that replaces it: same dispatch, plus a device key (`X-Sync-Key` header) and a cap of 9 dispatches per UTC day with 3 minutes between them (3,368 bytes) | `b85bdb1e2a03cd51f4c1ff9e19b5fd2d28cf468622312716d4861984526f57d8` |

> **Val Town is winding down**: read-only from **2026-12-10**, all services end **2027-01-10** (blog.val.town/winding-down). Cutover to the Worker (§5) must happen before 2026-12-10. Until then the val stays live and §1 still works.

## 1. Recreate the val (Val Town, until 2026-12-10)

1. val.town → New → **HTTP** val, name `redline-sync`, paste `relay/main.ts` as `main.ts`, save. Public is fine.
2. Open the val's **Environment variables** tab (per-val — *not* account settings) and add **`GH_TOKEN`** = the `redline-sync-relay` token (§2).
3. Copy the val's web endpoint (`https://joegrimaldi--<id>.web.val.run`) into **`SYNC_URL`** in `build/tail.html`, commit, push. That push rebuilds and deploys the app.
4. Test: a GET returns **405 "POST only"**; `curl -X POST <endpoint>` returns **"Sync started"** and a new *Redline Strava Sync* run with event `workflow_dispatch` appears in the Actions tab within seconds.

## 2. The relay token

- Name: **`redline-sync-relay`** — a fine-grained personal access token. Repository access: **only `joegrimaldi/redline`**. Permissions: **Actions: Read and write** (Metadata: read is implied). **Nothing else — never Contents: write.** With the val the endpoint is public and unauthenticated; with the Worker the device key is the lock. Either way the token must only be able to start a sync, never change the repo.
- Rotation: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → `redline-sync-relay` → **Regenerate** → paste the new value into the relay's `GH_TOKEN` (Worker secret, or the val's env var) → run the test in §1 step 4 or §5. 🔄 is broken from the moment of regeneration until `GH_TOKEN` is updated.
- Check the expiry date whenever you are in there; an expired token makes 🔄 report `GitHub 401`.

## 3. Manual fallback (relay down, token expired, host gone)

GitHub → `joegrimaldi/redline` → **Actions** → *Redline Strava Sync* → **Run workflow** → branch `main`. This is exactly what the relay does. A push to anything under `build/**` also runs it.

## 4. Other credentials (names only)

- **`redline-local-push`** — fine-grained PAT, `joegrimaldi/redline` only, **Contents: read/write**. Used only for git pushes; lives in `.git/.credentials` (helper `store --file=.git/.credentials`, relative path) and the macOS keychain. Regenerating it stales both copies. It has no `workflow` scope, so `.github/workflows/*` can only be changed through the GitHub UI or a token that has it.
- Repo secrets read by `sync.yml` (Settings → Secrets and variables → Actions): **`STRAVA_CLIENT_ID`**, **`STRAVA_CLIENT_SECRET`**, **`STRAVA_REFRESH_TOKEN`**. If Strava auth fails in the workflow log, re-authorize the app in Strava's API settings, obtain a fresh refresh token and update the secret.

## 5. The Cloudflare Worker (`relay/worker.ts`)

**Bindings** (Worker → Settings): secret **`GH_TOKEN`** (the `redline-sync-relay` token), secret **`SYNC_KEY`** (the device key; a random 24-character string you generate — it is never written down in any repo or doc), KV namespace binding **`SYNC_KV`** → namespace `redline-sync`. CORS is limited to `https://joegrimaldi.github.io`.

**Behaviour**: `OPTIONS` → 204 · not `POST` → 405 · wrong or missing `X-Sync-Key` → 401 · more than 9 dispatches in a UTC day, or one within 180 s of the last → 429 with the reason in the body · GitHub refuses → **502** `GitHub <status>: <message>` · success → 200 `Sync started`. The app shows the 401/429/502 text in a toast; on 401 it forgets the stored key and asks again next tap.

**The app side**: the key is entered once per device through a `prompt()`, kept in `localStorage` under `syncKey`, sent as `X-Sync-Key`. Only the header name is in `build/tail.html`. The app's Update button clears caches and the service worker but not `localStorage`, so the key survives updates.

**Recreate from scratch**: dash.cloudflare.com → Workers & Pages → Create → Worker named `redline-sync` → Edit code → paste `relay/worker.ts` → Deploy; Storage & Databases → KV → create `redline-sync`; Worker → Settings → Bindings → add KV `SYNC_KV`; Settings → Variables and Secrets → add secrets `GH_TOKEN`, `SYNC_KEY`; Deploy. Then `SYNC_URL` in `build/tail.html` = `https://redline-sync.<account-subdomain>.workers.dev`.

**Test** (Terminal): `curl -i <url>` → 405; `curl -i -X POST <url>` → 401; `curl -i -X POST -H "X-Sync-Key: <key>" <url>` → `Sync started` and a `workflow_dispatch` run in the Actions tab; a second POST within 3 min → 429.

**Cutover order** (sync never breaks): deploy and test the Worker while the val is still live → push `build/tail.html` with the key change and the new `SYNC_URL` → open the app on the phone, tap 🔄, enter the key once → after one successful sync, regenerate `redline-sync-relay`, put the new value in the Worker's `GH_TOKEN`, test again → delete the val. Rollback at any point before the token rotation is a one-line push of `SYNC_URL` back to the val.

## 6. Verify the mirrors

`shasum -a 256 relay/main.ts relay/worker.ts` must match the table above. Whenever the live relay code changes, update the file, the hash and this section in the same commit.
