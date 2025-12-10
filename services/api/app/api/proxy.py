"""
Proxy endpoint for fetching external URLs and stripping X-Frame-Options headers.
Allows iframe embedding of external content that normally blocks it.
"""

from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter(tags=["proxy"])

# Whitelist of allowed domains for proxying (security measure)
ALLOWED_DOMAINS = [
    "my.osiris.brussels",
    "osiris.brussels",
    "ejustice.just.fgov.be",
    "www.ejustice.just.fgov.be",
    "mobilit.belgium.be",
    "www.mobilit.belgium.be",
]


def is_domain_allowed(url: str) -> bool:
    """Check if the URL's domain is in the whitelist."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(
            domain == allowed or domain.endswith(f".{allowed}") for allowed in ALLOWED_DOMAINS
        )
    except Exception:
        return False


@router.get("/proxy")
async def proxy_url(
    url: str = Query(..., description="URL to proxy"),
) -> Response:
    """
    Proxy external URLs to bypass X-Frame-Options restrictions.

    Only whitelisted domains are allowed for security reasons.
    Strips X-Frame-Options and CSP headers from the response.
    """
    # Validate URL
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400, detail="Invalid URL: must start with http:// or https://"
        )

    # Check domain whitelist
    if not is_domain_allowed(url):
        raise HTTPException(
            status_code=403,
            detail=f"Domain not allowed. Whitelisted: {', '.join(ALLOWED_DOMAINS)}",
        )

    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; RAG-Proxy/1.0)",
            },
        ) as client:
            response = await client.get(url)

            # Build response headers, stripping restrictive ones
            headers = {}
            for key, value in response.headers.items():
                key_lower = key.lower()
                # Skip headers that block iframe embedding
                if key_lower in (
                    "x-frame-options",
                    "content-security-policy",
                    "x-content-security-policy",
                ):
                    continue
                # Skip hop-by-hop headers
                if key_lower in ("transfer-encoding", "connection", "keep-alive"):
                    continue
                headers[key] = value

            # Add permissive CSP for framing
            headers["X-Frame-Options"] = "ALLOWALL"
            headers["Content-Security-Policy"] = "frame-ancestors *"

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=headers,
                media_type=response.headers.get("content-type", "text/html"),
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timed out")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {str(e)}")
