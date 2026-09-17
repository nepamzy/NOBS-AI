"""Vercel connector — scoped to ONE project (VERCEL_PROJECT_ID), hardcoded
server-side rather than taken from the LLM's tool input, same reasoning as
the GitHub connector: a bad tool call can't redirect it at a different
project. Read access (deployments, env var names) plus write access to
env vars only — never trigger a deploy, never delete/pause the project,
never touch domains. "Read and write and edit, not push" per Nobert's
instruction: env var changes take effect on the *next* deploy Nobert
triggers himself (from git push or the dashboard), not immediately.

The exact endpoint versions below (v6/v9/v10) are current as documented,
but — like the Runpod/Wan adapter — flagged as unverified against a real
account until the first real call; Vercel has changed API versions
between endpoints before.
"""

import httpx

from services.common.errors import EngineNotConfiguredError

_API_BASE_URL = "https://api.vercel.com"
_REQUEST_TIMEOUT_SECONDS = 30


class VercelConnector:
    def __init__(self, token: str, project_id: str, team_id: str = ""):
        self._token = token
        self._project_id = project_id
        self._team_id = team_id

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def _params(self, **extra) -> dict:
        params = {"projectId": self._project_id, **extra}
        if self._team_id:
            params["teamId"] = self._team_id
        return params

    def _require_configured(self) -> None:
        if not self._token or not self._project_id:
            raise EngineNotConfiguredError(
                "No VERCEL_API_TOKEN/VERCEL_PROJECT_ID configured — the "
                "Vercel connector needs an API token scoped to one project."
            )

    def list_deployments(self, limit: int = 10) -> list[dict]:
        self._require_configured()
        response = httpx.get(
            f"{_API_BASE_URL}/v7/deployments",
            headers=self._headers(),
            params=self._params(limit=limit),
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["deployments"]

    def get_deployment(self, deployment_id: str) -> dict:
        self._require_configured()
        response = httpx.get(
            f"{_API_BASE_URL}/v13/deployments/{deployment_id}",
            headers=self._headers(),
            params={"teamId": self._team_id} if self._team_id else {},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def list_env_vars(self) -> list[dict]:
        """Names/targets only — Vercel doesn't return decrypted values on
        the list endpoint, so this can't leak secrets back through chat."""
        self._require_configured()
        response = httpx.get(
            f"{_API_BASE_URL}/v9/projects/{self._project_id}/env",
            headers=self._headers(),
            params={"teamId": self._team_id} if self._team_id else {},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return [
            {"id": e["id"], "key": e["key"], "target": e.get("target", [])}
            for e in response.json()["envs"]
        ]

    def set_env_var(self, key: str, value: str, target: list[str] | None = None) -> dict:
        self._require_configured()
        response = httpx.post(
            f"{_API_BASE_URL}/v10/projects/{self._project_id}/env",
            headers=self._headers(),
            params={"teamId": self._team_id} if self._team_id else {},
            json={
                "key": key,
                "value": value,
                "type": "encrypted",
                "target": target or ["production"],
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        # Returned verbatim rather than picking out one nested field — the
        # exact response shape isn't independently verified against a real
        # account yet (see module docstring).
        return response.json()
