from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("Mexico Zip Codes API")

BASE_URL = "https://mexico-zip-codes.p.rapidapi.com"
RAPIDAPI_HOST = "mexico-zip-codes.p.rapidapi.com"
VALIDATE_HEADER_VALUE = os.environ.get("VALIDATE_HEADER_VALUE", "")


def build_headers(api_key: str) -> dict:
    return {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
    }


@mcp.tool()
async def get_api_info() -> dict:
    """Returns a welcome message with general information about the Mexico Zip Codes API. Use this to verify the API is reachable or to get an overview of its capabilities."""
    fallback_api_key = VALIDATE_HEADER_VALUE
    headers = build_headers(fallback_api_key)
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(f"{BASE_URL}/", headers=headers)
        return {
            "status_code": response.status_code,
            "content": response.text,
        }


@mcp.tool()
async def lookup_postal_code(
    codigo_postal: str,
    api_key: str,
    use_v2: Optional[bool] = False,
) -> dict:
    """Returns all colonias (neighborhoods), municipio (municipality), and estado (state) associated with a given Mexican postal code. Use this when you have an exact postal code and need full location details. Returns grouped colonias array in v2 format when use_v2 is true."""
    headers = build_headers(api_key)
    if use_v2:
        url = f"{BASE_URL}/v2/codigo_postal/{codigo_postal}"
    else:
        url = f"{BASE_URL}/codigo_postal/{codigo_postal}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        try:
            data = response.json()
        except Exception:
            data = response.text
        return {
            "status_code": response.status_code,
            "codigo_postal": codigo_postal,
            "use_v2": use_v2,
            "data": data,
        }


@mcp.tool()
async def search_postal_codes_by_prefix(
    prefix: str,
    api_key: str,
    limit: Optional[int] = None,
    use_v2: Optional[bool] = False,
) -> dict:
    """Returns a list of distinct Mexican postal codes that match a given prefix string. Use this for autocomplete or when the user knows only the beginning of a postal code. The v2 version supports an optional result limit."""
    headers = build_headers(api_key)
    if use_v2:
        url = f"{BASE_URL}/v2/buscar"
        params: dict = {"codigo_postal": prefix}
        if limit is not None and limit > 0:
            params["limit"] = limit
    else:
        url = f"{BASE_URL}/buscar"
        params = {"q": prefix}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers, params=params)
        try:
            data = response.json()
        except Exception:
            data = response.text
        return {
            "status_code": response.status_code,
            "prefix": prefix,
            "use_v2": use_v2,
            "limit": limit,
            "data": data,
        }


@mcp.tool()
async def search_postal_codes_by_location(
    estado: str,
    municipio: str,
    api_key: str,
    colonia: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict:
    """Returns postal codes filtered by estado (state) and municipio (municipality), with an optional colonia (neighborhood) filter and result limit. Use this when the user knows the location name but not the postal code — ideal for reverse location-to-code lookups."""
    headers = build_headers(api_key)
    url = f"{BASE_URL}/v2/buscar_por_ubicacion"
    params: dict = {
        "estado": estado,
        "municipio": municipio,
    }
    if colonia:
        params["colonia"] = colonia
    if limit is not None and limit > 0:
        params["limit"] = limit

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers, params=params)
        try:
            data = response.json()
        except Exception:
            data = response.text
        return {
            "status_code": response.status_code,
            "estado": estado,
            "municipio": municipio,
            "colonia": colonia,
            "limit": limit,
            "data": data,
        }




_SERVER_SLUG = "acrogenesis-api-codigos-postales"

def _track(tool_name: str, ua: str = ""):
    try:
        import urllib.request, json as _json
        data = _json.dumps({"slug": _SERVER_SLUG, "event": "tool_call", "tool": tool_name, "user_agent": ua}).encode()
        req = urllib.request.Request("https://www.volspan.dev/api/analytics/event", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass

async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

sse_app = mcp.http_app(transport="sse")

app = Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", sse_app),
    ],
    lifespan=sse_app.lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
