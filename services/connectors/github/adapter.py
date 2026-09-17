"""GitHub connector — deliberately scoped to ONE repo (GITHUB_DEFAULT_REPO),
hardcoded server-side rather than taken from the LLM's tool input, so a bad
tool call (or a prompt-injection attempt from something the model read)
can't redirect it at a different repository Nobert didn't approve.

No direct push to the default branch and no force-push: writes always land
on a new branch, surfaced as a pull request for Nobert to actually merge —
"read/write/edit, not push and send" per his explicit instruction. Never
implemented: delete repo/branch, force-push, merge, or anything outside
Contents/Pull requests — a fine-grained PAT scoped to just those two
permissions on just this repo is what GITHUB_TOKEN should be.

Real REST calls from the first write — this isn't paid, so no
ApprovalRequiredError gate, but it IS a real, externally-visible action
(a real commit, a real PR), so EngineNotConfiguredError until set up, and
every call result should be shown to Nobert plainly, not hidden.
"""

import base64

import httpx

from services.common.errors import EngineNotConfiguredError

_API_BASE_URL = "https://api.github.com"
_REQUEST_TIMEOUT_SECONDS = 30


class GitHubConnector:
    def __init__(self, token: str, repo: str):
        self._token = token
        self._repo = repo

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _require_configured(self) -> None:
        if not self._token or not self._repo:
            raise EngineNotConfiguredError(
                "No GITHUB_TOKEN/GITHUB_DEFAULT_REPO configured — the "
                "GitHub connector needs a fine-grained personal access "
                "token scoped to Contents + Pull requests on one repo."
            )

    def read_file(self, path: str, ref: str = "main") -> str:
        self._require_configured()
        response = httpx.get(
            f"{_API_BASE_URL}/repos/{self._repo}/contents/{path}",
            headers=self._headers(),
            params={"ref": ref},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        return base64.b64decode(payload["content"]).decode("utf-8")

    def create_branch(self, branch_name: str, from_branch: str = "main") -> None:
        self._require_configured()
        base_ref = httpx.get(
            f"{_API_BASE_URL}/repos/{self._repo}/git/ref/heads/{from_branch}",
            headers=self._headers(),
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        base_ref.raise_for_status()
        base_sha = base_ref.json()["object"]["sha"]

        response = httpx.post(
            f"{_API_BASE_URL}/repos/{self._repo}/git/refs",
            headers=self._headers(),
            json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    def write_file(self, path: str, content: str, message: str, branch: str) -> str:
        """Creates or updates a file on `branch` (never the default branch
        directly). Returns the commit's html_url."""
        self._require_configured()
        existing_sha = None
        existing = httpx.get(
            f"{_API_BASE_URL}/repos/{self._repo}/contents/{path}",
            headers=self._headers(),
            params={"ref": branch},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        if existing.status_code == 200:
            existing_sha = existing.json()["sha"]

        body = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if existing_sha:
            body["sha"] = existing_sha

        response = httpx.put(
            f"{_API_BASE_URL}/repos/{self._repo}/contents/{path}",
            headers=self._headers(),
            json=body,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["commit"]["html_url"]

    def create_pull_request(self, branch: str, title: str, body: str, base: str = "main") -> str:
        """Returns the PR's html_url. This is the ONLY way changes reach the
        default branch — never merged automatically, always left for Nobert
        to review and merge himself."""
        self._require_configured()
        response = httpx.post(
            f"{_API_BASE_URL}/repos/{self._repo}/pulls",
            headers=self._headers(),
            json={"title": title, "head": branch, "base": base, "body": body},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["html_url"]
