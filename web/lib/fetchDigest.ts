import type { Digest } from "./types";

/**
 * Fetch the latest digest directly from the GitHub raw URL so the PWA always
 * shows fresh data on open (no rebuild required when the daily Action commits).
 */
export async function fetchDigest(): Promise<Digest> {
  const owner = process.env.NEXT_PUBLIC_GITHUB_OWNER ?? "Possum-Parker";
  const repo = process.env.NEXT_PUBLIC_GITHUB_REPO ?? "morning-digest";
  const branch = process.env.NEXT_PUBLIC_GITHUB_BRANCH ?? "main";

  const url = `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/data/latest.json?ts=${Date.now()}`;

  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to load digest (${res.status})`);
  }
  return (await res.json()) as Digest;
}
