# Relay recovery — `redline-sync`

The 🔄 Sync button in the app POSTs to a tiny HTTP relay; the relay calls GitHub's `workflow_dispatch` on `.github/workflows/sync.yml` with an Actions-only token. `relay/main.ts` in this folder is a **verbatim mirror of the live Val Town val** `joegrimaldi/redline-sync` (captured 2026-11-12: 1,129 bytes, 32 lines, no trailing newline, SHA-256 `2d755cbfd3683fa9bac2fd835c821320d066d8272d9da063ce1dc72392984973`). The source holds no secret — only the env var *name*.

> **Val Town is winding down**: read-only from **2026-12-10**, all services end **2027-01-10** (blog.val.town/winding-down). The relay has to move to another host before then — see §5. Until 2026-12-10 the val can still be recreated as in §1.

## 1. Recreate the val (Val Town, until 2026-12-10)

1. val.town → New → **HTTP** val, name `redline-sync`, paste `relay/main.ts` as `main.ts`, save. Public is fine.
2. Open the val's **Environment variables** tab (per-val — *not* account settings) and add **`GH_TOKEN`** = the `redline-sync-relay` token (§2).
3. Copy the val's web endpoint (`https://joegrimaldi--<id>.web.val.run`) into **`SYNC_URL`** in `build/tail.html` (one constant, ~line 328), commit, push. That push rebuilds and deploys the app.
4. Test: a GET to the endpoint returns **405 "POST only"**; `curl -X POST <endpoint>` returns **"Sync started"** and a new *Redline Strava Sync* run with event `workflow_dispatch` appears in the Actions tab within seconds. Anything else comes back as `GitHub <status> (...)` with GitHub's message.

## 2. The relay token

- Name: **`redline-sync-relay`** — a fine-grained personal access token. Repository access: **only `joegrimaldi/redline`**. Permissions: **Actions: Read and write** (Metadata: read is implied). **Nothing else — never Contents: write.** The endpoint is public and unauthenticated, so this token must only be able to start a sync, never change the repo.
- Rotation: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → `redline-sync-relay` → **Regenerate** → paste the new value into the val's `GH_TOKEN` → run the §1 test. 🔄 is broken from the moment of regeneration until `GH_TOKEN` is updated.
- Check the expiry date whenever you are in there; an expired token makes 🔄 report "failed" with `GitHub 401`.

## 3. Manual fallback (relay down, token expired, Val Town gone)

GitHub → `joegrimaldi/redline` → **Actions** → *Redline Strava Sync* → **Run workflow** → branch `main`. This is exactly what the relay does. A push to anything under `build/**` also runs it.

## 4. Other credentials (names only)

- **`redline-local-push`** — fine-grained PAT, `joegrimaldi/redline` only, **Contents: read/write**. Used only for git pushes; lives in `.git/.credentials` (helper `store --file=.git/.credentials`, relative path) and the macOS keychain. Regenerating it stales both copies. It has no `workflow` scope, so `.github/workflows/*` can only be changed through the GitHub UI or a token that has it.
- Repo secrets read by `sync.yml` (Settings → Secrets and variables → Actions): **`STRAVA_CLIENT_ID`**, **`STRAVA_CLIENT_SECRET`**, **`STRAVA_REFRESH_TOKEN`**. If Strava auth fails in the workflow log, re-authorize the app in Strava's API settings, obtain a fresh refresh token and update the secret.

## 5. Re-host (required before 2027-01-10)

`main.ts` is a plain `(Request) => Promise<Response>` handler with one platform call, `Deno.env.get("GH_TOKEN")`. Any edge/function host runs it with a one-line change:

- **Cloudflare Workers** — wrap as `export default { fetch(req, env) { ... } }` and read `env.GH_TOKEN`; set `GH_TOKEN` as a Worker secret.
- **Deno Deploy** — keep the file; add `Deno.serve(handler)`; set `GH_TOKEN` in the project's env vars.
- Netlify / Vercel edge functions — same handler, their env var UI.

After re-hosting: set `GH_TOKEN` there, update `SYNC_URL` in `build/tail.html`, push, run the §1 test, then **rotate `redline-sync-relay`** so the copy left on Val Town is dead. Keep `relay/main.ts` updated to whatever is live.

## 6. Verify the mirror

`shasum -a 256 relay/main.ts` must match the SHA-256 above; the live val's source hashes to the same value (captured via the editor's document text). If the val is edited, update this file and the hash in the same commit.
