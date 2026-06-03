/**
 * API for editing a single holding in config/holdings.json.
 *
 * Auth: requires X-Edit-Token header matching EDIT_TOKEN env var. The PWA stores
 * this token in localStorage after the user enters it once; without it, randos who
 * find the URL can read holdings (already public in the repo) but can't change them.
 *
 * On PUT/DELETE: we fetch the current holdings.json from GitHub, mutate in memory,
 * then PUT the new file back to GitHub with the original sha (so concurrent edits
 * fail cleanly). The next workflow run will pick up the change.
 */

export const dynamic = "force-dynamic";

const GITHUB_API = "https://api.github.com";
const HOLDINGS_PATH = "config/holdings.json";

function unauthorized() {
  return new Response("Unauthorized", { status: 401 });
}

function tokenValid(request: Request): boolean {
  const expected = process.env.EDIT_TOKEN;
  if (!expected) return false; // refuse if env not configured
  const provided = request.headers.get("x-edit-token");
  return provided === expected;
}

function repoIdentity() {
  return {
    owner: process.env.GITHUB_OWNER ?? "Possum-Parker",
    repo: process.env.GITHUB_REPO ?? "morning-digest",
    token: process.env.GITHUB_TOKEN,
  };
}

async function fetchHoldings(owner: string, repo: string, token: string) {
  const r = await fetch(
    `${GITHUB_API}/repos/${owner}/${repo}/contents/${HOLDINGS_PATH}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "morning-digest-editor",
      },
      cache: "no-store",
    },
  );
  if (!r.ok) {
    throw new Error(`GitHub GET ${r.status}: ${await r.text()}`);
  }
  const payload = (await r.json()) as { content: string; sha: string };
  const content = JSON.parse(
    Buffer.from(payload.content, "base64").toString("utf-8"),
  );
  return { content, sha: payload.sha };
}

async function writeHoldings(
  owner: string,
  repo: string,
  token: string,
  newContent: Record<string, unknown>,
  sha: string,
  commitMessage: string,
) {
  const newBase64 = Buffer.from(
    JSON.stringify(newContent, null, 2) + "\n",
  ).toString("base64");
  const r = await fetch(
    `${GITHUB_API}/repos/${owner}/${repo}/contents/${HOLDINGS_PATH}`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "morning-digest-editor",
      },
      body: JSON.stringify({
        message: commitMessage,
        content: newBase64,
        sha,
      }),
    },
  );
  if (!r.ok) {
    throw new Error(`GitHub PUT ${r.status}: ${await r.text()}`);
  }
}

export async function PUT(
  request: Request,
  { params }: { params: { ticker: string } },
) {
  if (!tokenValid(request)) return unauthorized();

  const ticker = decodeURIComponent(params.ticker);
  let body: { shares?: number; total_invested?: number };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const shares = Number(body.shares);
  const totalInvested = Number(body.total_invested);
  if (!Number.isFinite(shares) || shares < 0) {
    return Response.json({ error: "shares must be a non-negative number" }, { status: 400 });
  }
  if (!Number.isFinite(totalInvested) || totalInvested < 0) {
    return Response.json(
      { error: "total_invested must be a non-negative number" },
      { status: 400 },
    );
  }

  const { owner, repo, token } = repoIdentity();
  if (!token) {
    return Response.json({ error: "GITHUB_TOKEN not configured" }, { status: 500 });
  }

  try {
    const { content, sha } = await fetchHoldings(owner, repo, token);
    content[ticker] = { shares, total_invested: totalInvested };
    await writeHoldings(owner, repo, token, content, sha, `holdings: update ${ticker}`);
    return Response.json({ ok: true, ticker, shares, total_invested: totalInvested });
  } catch (e) {
    return Response.json(
      { error: e instanceof Error ? e.message : String(e) },
      { status: 502 },
    );
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: { ticker: string } },
) {
  if (!tokenValid(request)) return unauthorized();

  const ticker = decodeURIComponent(params.ticker);
  const { owner, repo, token } = repoIdentity();
  if (!token) {
    return Response.json({ error: "GITHUB_TOKEN not configured" }, { status: 500 });
  }

  try {
    const { content, sha } = await fetchHoldings(owner, repo, token);
    if (!(ticker in content)) {
      return Response.json({ ok: false, error: "Ticker not in holdings" }, { status: 404 });
    }
    delete content[ticker];
    await writeHoldings(owner, repo, token, content, sha, `holdings: remove ${ticker}`);
    return Response.json({ ok: true, ticker, removed: true });
  } catch (e) {
    return Response.json(
      { error: e instanceof Error ? e.message : String(e) },
      { status: 502 },
    );
  }
}
