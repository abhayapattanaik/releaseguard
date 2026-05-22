"""Local test script — simulates a GitHub PR webhook hitting ReleaseGuard."""

import asyncio
import json

import httpx


SAMPLE_WEBHOOK = {
    "action": "opened",
    "pull_request": {
        "number": 1,
        "title": "Add user authentication",
        "body": "Implements login endpoint with SQL queries",
        "head": {"sha": "abc123"},
    },
    "repository": {"full_name": "test-org/test-repo"},
}


async def main():
    url = "http://localhost:8000"

    # 1. Health check
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{url}/health")
        print(f"Health: {resp.json()}")

        # 2. Send fake webhook
        print("\nSending test webhook...")
        resp = await client.post(
            f"{url}/webhook",
            content=json.dumps(SAMPLE_WEBHOOK),
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "pull_request",
            },
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
