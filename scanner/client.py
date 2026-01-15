"""
wekan API Client

Handles authentication and base HTTP client configuration.
"""

from typing import Any, TYPE_CHECKING
import httpx
import logfire
from scanner.models import APIModel

# TYPE_CHECKING allows forward references without circular imports
if TYPE_CHECKING:
    pass  # Add forward references here if needed


class APIResponse:
    """
    Wrapper around httpx.Response with JSON parsing helpers.

    Provides convenient methods for parsing API responses into models.
    """

    def __init__(self, response: httpx.Response):
        self._response = response
        self._json: dict[str, Any] = {}

    @property
    def response(self) -> httpx.Response:
        """Access the underlying httpx.Response."""
        return self._response

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._response.status_code

    @property
    def json(self) -> dict[str, Any]:
        """Parse response as JSON (cached)."""
        if not self._json:
            try:
                self._json = self._response.json()
            except httpx.DecodingError:
                logfire.warn("Response body is not valid JSON, returning empty dict.")
                self._json = {}
        return self._json

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the JSON response."""
        return self.json.get(key, default)

    def success(self) -> bool:
        """Check if response has success=True (common API pattern)."""
        return self.json.get('success', False)

    def as_model[T: APIModel](self, model_cls: type[T], *keys: str) -> T:
        """
        Parse response as a single model instance.

        Args:
            model_cls: The Pydantic model class to parse into
            *keys: Keys to try in order. If none provided, parses root object.
                   Use multiple keys for APIs with inconsistent response shapes.

        Example:
            # Response: {"team": {...}}
            team = response.as_model(Team, 'team')

            # Response might have "team" or "teamInfo"
            team = response.as_model(Team, 'team', 'teamInfo')
        """
        if keys:
            for key in keys:
                if key in self.json:
                    return model_cls(**self.json[key])
            # None of the keys found, try root
        return model_cls(**self.json)

    def as_list[T: APIModel](self, model_cls: type[T], key: str) -> list[T]:
        """
        Parse response as a list of model instances.

        Args:
            model_cls: The Pydantic model class to parse each item into
            key: The key containing the list in the response

        Example:
            # Response: {"teams": [{...}, {...}]}
            teams = response.as_list(Team, 'teams')
        """
        items = self.json.get(key, [])
        return [model_cls(**item) for item in items]


class WekanClientConfig(APIModel):
    """Configuration for wekan API client."""

    base_url: str
    """Base URL of the wekan instance."""


    token: str | None = None
    """Authentication token for the API."""

    timeout: float = 30.0
    verify_ssl: bool = True


class WekanClient:
    """
    HTTP client for wekan API.

    Handles authentication, request signing, and base configuration.

    Usage:
        config = WekanClientConfig(
            base_url="http://localhost:3000",
        )
        async with WekanClient(config) as client:
            # GET request (default method)
            teams = (await client.get('teams.list')).as_list(Team, 'teams')

            # POST request
            team = (await client.post('teams.create', json=payload)).as_model(Team, 'team')
    """

    def __init__(self, config: WekanClientConfig):
        """
        Initialize the client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.client = self._create_client()

    def _create_client(self) -> httpx.AsyncClient:
        """Create the HTTP client with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"

        return httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=headers,
            timeout=self.config.timeout,
            verify=self.config.verify_ssl,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    def _resolve_endpoint(self, endpoint: str) -> str:
        """Resolve endpoint path.

        - Absolute paths (starting with /) are used as-is
        - Relative paths are used as-is

        The generator should pass full paths (e.g. "/api/v1/teams.list")
        if the target API uses a common prefix.
        """
        return endpoint

    async def request(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs: Any
    ) -> httpx.Response:
        """
        Make an authenticated request.

        Args:
            endpoint: API endpoint path (relative to prefix, or absolute if starts with /)
            method: HTTP method (GET, POST, PUT, DELETE). Defaults to GET.
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Response object
        """
        resolved = self._resolve_endpoint(endpoint)
        logfire.debug(f"{method} {resolved}", method=method, endpoint=resolved)
        response = await self.client.request(method, resolved, **kwargs)
        response.raise_for_status()
        return response

    async def get(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """
        Make a GET request and return wrapped response.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments (params, headers, etc.)

        Returns:
            APIResponse wrapper with parsing helpers
        """
        return APIResponse(await self.request(endpoint, "GET", **kwargs))

    async def post(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """
        Make a POST request and return wrapped response.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments (json, data, headers, etc.)

        Returns:
            APIResponse wrapper with parsing helpers
        """
        return APIResponse(await self.request(endpoint, "POST", **kwargs))

    async def put(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """
        Make a PUT request and return wrapped response.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments (json, data, headers, etc.)

        Returns:
            APIResponse wrapper with parsing helpers
        """
        return APIResponse(await self.request(endpoint, "PUT", **kwargs))

    async def delete(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """
        Make a DELETE request and return wrapped response.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments

        Returns:
            APIResponse wrapper with parsing helpers
        """
        return APIResponse(await self.request(endpoint, "DELETE", **kwargs))
