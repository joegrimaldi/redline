export default async function (req: Request): Promise<Response> {
  const cors = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  if (req.method !== "POST") {
    return new Response("POST only", { status: 405, headers: cors });
  }
  const tok = Deno.env.get("GH_TOKEN");
  const r = await fetch(
    "https://api.github.com/repos/joegrimaldi/redline/actions/workflows/sync.yml/dispatches",
    {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + tok,
        "Accept": "application/vnd.github+json",
        "User-Agent": "redline-sync-relay",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({ ref: "main" }),
    },
  );
  const body = await r.text();
  const ok = r.status === 204;
  const dbg = "tokenLen=" + (tok ? tok.length : 0);
  return new Response(
    ok ? "Sync started" : ("GitHub " + r.status + " (" + dbg + "): " + body),
    { status: 200, headers: cors },
  );
}