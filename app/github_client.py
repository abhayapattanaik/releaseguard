import asyncio
import os
from typing import Any

import httpx

_BASE = "https://api.github.com"


def _headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def get_pr_info(repo: str, pr_number: int) -> dict[str, Any] | None:
    """Fetch PR metadata: title, body, sha, changed_files list."""
    url = f"{_BASE}/repos/{repo}/pulls/{pr_number}"
    files_url = f"{url}/files"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            pr_resp, files_resp = await asyncio.gather(
                client.get(url, headers=_headers()),
                client.get(files_url, headers=_headers()),
            )
            pr_resp.raise_for_status()
            files_resp.raise_for_status()

        pr = pr_resp.json()
        files = files_resp.json()

        return {
            "title": pr.get("title", ""),
            "body": pr.get("body", "") or "",
            "sha": pr.get("head", {}).get("sha", ""),
            "changed_files": [f["filename"] for f in files],
        }
    except Exception:
        return None


async def post_comment(repo: str, pr_number: int, body: str) -> bool:
    """Post a comment on a PR. Returns True on success."""
    url = f"{_BASE}/repos/{repo}/issues/{pr_number}/comments"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=_headers(), json={"body": body})
            resp.raise_for_status()
        return True
    except Exception:
        return False


async def clone_repo(repo: str, sha: str, target_dir: str) -> bool:
    """Shallow-clone repo at sha into target_dir. Returns True on success."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        clone_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    else:
        clone_url = f"https://github.com/{repo}.git"

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone",
            "--depth", "1",
            "--no-single-branch",
            clone_url,
            target_dir,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()

        if proc.returncode != 0:
            return False

        checkout = await asyncio.create_subprocess_exec(
            "git", "-C", target_dir, "checkout", sha,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await checkout.communicate()
        return checkout.returncode == 0
    except Exception:
        return False
