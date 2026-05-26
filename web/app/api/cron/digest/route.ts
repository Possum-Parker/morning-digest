/**
 * Vercel Cron handler — fires daily at 5:30 PM AEST (07:30 UTC).
 *
 * Triggers the GitHub Actions workflow via the workflow_dispatch API. We use Vercel Cron
 * as the scheduler (instead of GitHub Actions' built-in cron) because GitHub's scheduler
 * is well-documented to delay or skip scheduled runs on personal/shared infrastructure.
 * Vercel runs on dedicated infrastructure with much better reliability guarantees.
 *
 * Auth: Vercel Cron automatically sends `Authorization: Bearer ${CRON_SECRET}` on every
 * invocation, so we reject anything else (prevents the public route from being abused).
 */

export const dynamic = "force-dynamic";

const GITHUB_API = "https://api.github.com";

export async function GET(request: Request) {
  // 1) Verify the request came from Vercel Cron
  const expected = process.env.CRON_SECRET;
  if (expected) {
    const authHeader = request.headers.get("authorization");
    if (authHeader !== `Bearer ${expected}`) {
      return new Response("Unauthorized", { status: 401 });
    }
  }

  const owner = process.env.GITHUB_OWNER ?? "Possum-Parker";
  const repo = process.env.GITHUB_REPO ?? "morning-digest";
  const workflow = process.env.GITHUB_WORKFLOW_FILE ?? "daily-digest.yml";
  const ref = process.env.GITHUB_BRANCH ?? "main";
  const token = process.env.GITHUB_TOKEN;

  if (!token) {
    return Response.json(
      { ok: false, error: "GITHUB_TOKEN is not configured in Vercel env vars" },
      { status: 500 },
    );
  }

  const url = `${GITHUB_API}/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;

  const ghResponse = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      "User-Agent": "morning-digest-cron",
    },
    body: JSON.stringify({ ref }),
  });

  // GitHub's workflow_dispatch returns 204 No Content on success.
  const bodyText = await ghResponse.text();
  const success = ghResponse.status === 204;

  return Response.json(
    {
      ok: success,
      github_status: ghResponse.status,
      github_body: bodyText.slice(0, 300),
      triggered_at: new Date().toISOString(),
      workflow,
      ref,
    },
    { status: success ? 200 : 502 },
  );
}
