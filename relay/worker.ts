// Cloudflare Worker — the 🔄 Sync relay for joegrimaldi/redline.
// Replaces the Val Town val (relay/main.ts) with a device key and a daily cap.
//
// Bindings (Worker → Settings):
//   GH_TOKEN  secret        fine-grained PAT "redline-sync-relay": Actions read/write on joegrimaldi/redline only
//   SYNC_KEY  secret        the device key the app sends in the X-Sync-Key header
//   SYNC_KV   KV namespace  holds the per-day counter and the last-dispatch time
//
// Responses: 200 "Sync started" | 401 bad/missing key | 405 not POST | 429 cap or spacing | 502 GitHub refused.

export interface Env {
  GH_TOKEN: string;
  SYNC_KEY: string;
  SYNC_KV: KVNamespace;
}

const CAP_PER_DAY = 9;   // dispatches per UTC day
const MIN_GAP_S = 180;   // seconds between dispatches (a sync takes ~2–3 min anyway)
const ORIGIN = "https://joegrimaldi.github.io";
const DISPATCH = "https://api.github.com/repos/joegrimaldi/redline/actions/workflows/sync.yml/dispatches";

const CORS = {
  "Access-Control-Allow-Origin": ORIGIN,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Sync-Key",
  "Access-Control-Max-Age": "86400",
};

function reply(text: string, status: number): Response {
  return new Response(text, { status, headers: { ...CORS, "Content-Type": "text/plain; charset=utf-8" } });
}

// Constant-time comparison so response timing says nothing about the key.
function sameKey(a: string, b: string): boolean {
  const x = new TextEncoder().encode(a), y = new TextEncoder().encode(b);
  if (x.length !== y.length) return false;
  let d = 0;
  for (let i = 0; i < x.length; i++) d |= x[i] ^ y[i];
  return d === 0;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (req.method !== "POST") return reply("POST only", 405);

    const key = req.headers.get("X-Sync-Key") || "";
    if (!env.SYNC_KEY || !sameKey(key, env.SYNC_KEY)) return reply("Sync key missing or wrong", 401);

    const now = Math.floor(Date.now() / 1000);
    const day = new Date().toISOString().slice(0, 10);
    const [countRaw, lastRaw] = await Promise.all([env.SYNC_KV.get("count:" + day), env.SYNC_KV.get("last")]);
    const count = parseInt(countRaw || "0", 10);
    const last = parseInt(lastRaw || "0", 10);
    if (count >= CAP_PER_DAY) return reply("Daily sync cap reached (" + CAP_PER_DAY + "/day, resets 00:00 UTC)", 429);
    if (now - last < MIN_GAP_S) return reply("A sync started " + (now - last) + "s ago — wait " + (MIN_GAP_S - (now - last)) + "s", 429);

    const r = await fetch(DISPATCH, {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + env.GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "redline-sync-relay",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ ref: "main" }),
    });
    if (r.status !== 204) {
      const body = (await r.text()).slice(0, 200);
      return reply("GitHub " + r.status + ": " + body, 502);
    }

    await Promise.all([
      env.SYNC_KV.put("count:" + day, String(count + 1), { expirationTtl: 2 * 86400 }),
      env.SYNC_KV.put("last", String(now)),
    ]);
    return reply("Sync started", 200);
  },
};
