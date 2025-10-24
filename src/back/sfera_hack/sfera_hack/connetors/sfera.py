from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from sfera_hack.config import config


class SferaAPIClient:
    """Client for interacting with Sfera API"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = config.sfera_api_base_url
        self.auth_url = config.sfera_auth_url
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Make HTTP request to Sfera API with error handling"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=f"{self.base_url}{endpoint}",
                    params=params,
                    json=json_data,
                    headers=self.headers,
                    timeout=timeout,
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 400:
                    raise HTTPException(
                        status_code=400, detail="Bad Request - Invalid parameters"
                    )
                elif response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="Unauthorized - Invalid or expired token",
                    )
                elif response.status_code == 403:
                    raise HTTPException(
                        status_code=403, detail="Forbidden - Insufficient permissions"
                    )
                elif response.status_code == 404:
                    raise HTTPException(
                        status_code=404, detail="Not Found - Resource not found"
                    )
                elif response.status_code == 500:
                    raise HTTPException(
                        status_code=500,
                        detail="Internal Server Error - External API error",
                    )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"External API error: {response.text}",
                    )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Gateway Timeout - External API request timed out",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Bad Gateway - Failed to connect to external API: {str(e)}",
            )

    async def get_projects(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get list of projects"""
        return await self._make_request("GET", "/projects", params=params)

    async def get_repositories(
        self, project_key: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get list of repositories for a project"""
        endpoint = f"/projects/{project_key}/repos"
        return await self._make_request("GET", endpoint, params=params)

    async def get_project_commits(
        self, project_key: str, repo_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get commits for a project repository"""
        endpoint = f"/projects/{project_key}/repos/{repo_name}/commits"
        return await self._make_request("GET", endpoint, params=params)

    async def get_pull_requests(
        self, project_key: str, repo_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get pull requests for a project repository"""
        endpoint = f"/projects/{project_key}/repos/{repo_name}/pull-requests"
        return await self._make_request("GET", endpoint, params=params)

    async def get_pull_request(
        self, project_key: str, repo_name: str, pr_id: int
    ) -> Dict[str, Any]:
        """Get specific pull request"""
        endpoint = f"/projects/{project_key}/repos/{repo_name}/pull-requests/{pr_id}"
        return await self._make_request("GET", endpoint)

    async def get_project_branches(
        self, project_key: str, repo_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get branches for a project repository"""
        endpoint = f"/projects/{project_key}/repos/{repo_name}/branches"
        return await self._make_request("GET", endpoint, params=params)


class SferaAuthClient:
    """Client for Sfera authentication"""

    def __init__(self):
        self.auth_url = config.sfera_auth_url

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Sfera platform"""
        try:
            login_data = {"username": username, "password": password}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.auth_url}/app/ppau/api/auth/login",
                    json=login_data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
                elif response.status_code == 400:
                    raise HTTPException(
                        status_code=400, detail="Bad request - Invalid login data"
                    )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Authentication failed: {response.text}",
                    )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504, detail="Authentication service timeout"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to connect to authentication service: {str(e)}",
            )


# Convenience functions for backward compatibility
async def get_sfera_client(access_token: str) -> SferaAPIClient:
    """Get Sfera API client instance"""
    return SferaAPIClient(access_token)


async def get_sfera_auth_client() -> SferaAuthClient:
    """Get Sfera authentication client instance"""
    return SferaAuthClient()
