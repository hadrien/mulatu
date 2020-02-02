from __future__ import annotations
from typing import Dict, Optional, Type
from urllib.parse import urljoin

import aiohttp
from pydantic import BaseModel


class BaseClient:
    def __init__(self, base_url: str):
        self._base_url: str = base_url
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()

    async def _http_call(self, method: Method) -> aiohttp.ClientResponse:
        url = urljoin(self._base_url, method._resource._path)
        response: aiohttp.ClientResponse = await self._session.request(
            method._verb, url
        )
        return response

    async def close_session(self):
        await self._session.close()


class Response(BaseModel):
    _original: aiohttp.ClientResponse


class Method:
    _verb: str

    def __init__(
        self, client: BaseClient, resource: Resource, response_type: Type[Response]
    ):
        self._client = client
        self._resource = resource
        self._response_type = response_type

    async def __call__(self) -> Response:
        client_response = await self._client._http_call(self)
        body = await client_response.json()
        return self._response_type(_original=client_response, body=body)


class Delete(Method):
    _verb: str = "delete"


class Get(Method):
    _verb: str = "get"


class Patch(Method):
    _verb: str = "patch"


class Post(Method):
    _verb: str = "post"


class Put(Method):
    _verb: str = "put"


class Resource:
    def __init__(
        self,
        client: BaseClient,
        path_parameters: Dict[str, str],
    ):
        self._client = client
        self._path_parameters = path_parameters
