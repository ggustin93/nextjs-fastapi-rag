# API Versioning Strategy

This document describes the API versioning strategy for the RAG Agent API.

## Current Version

**Version**: v1
**Base Path**: `/api/v1`
**Status**: Active (Stable)

## Versioning Strategy

### URL Path Prefix

We use URL path prefixes for API versioning:

```
https://api.example.com/api/v1/chat/stream
https://api.example.com/api/v2/chat/stream  (future)
```

**Why URL Path?**
- Clear and explicit version indication
- Easy to route and proxy
- Simple client implementation
- Works with any HTTP client

### Version Format

Versions follow semantic versioning principles:
- **Major versions** (v1, v2): Breaking changes, new base paths
- **Minor versions**: Backwards-compatible features (no URL change)
- **Patch versions**: Bug fixes (no URL change)

## Version Lifecycle

| Phase | Duration | Description |
|-------|----------|-------------|
| **Active** | Indefinite | Current stable version, receives features and fixes |
| **Deprecated** | 6 months | Still functional, no new features, security fixes only |
| **Sunset** | 3 months | Final warning period, returns deprecation headers |
| **Removed** | - | Endpoint returns 410 Gone |

### Current Status

| Version | Status | Sunset Date |
|---------|--------|-------------|
| v1 | Active | N/A |

## Migration Policy

### New Version Announcement

- New major versions announced **3 months** before release
- Migration guides published at announcement
- Beta access available for testing

### Deprecation Process

1. **Deprecation Header**: `Deprecation: true` added to responses
2. **Sunset Header**: `Sunset: <date>` indicates removal date
3. **Documentation**: Updated with migration instructions
4. **Notifications**: API consumers notified via changelog

### Breaking Changes

Breaking changes ONLY occur in major version increments:
- Removed endpoints
- Changed response structures
- Modified authentication requirements
- Renamed fields (without aliases)

**Non-breaking changes** (can happen in any version):
- New optional fields
- New endpoints
- Performance improvements
- Bug fixes

## API Endpoints by Version

### v1 Endpoints (Current)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/stream` | Stream chat responses |
| GET | `/api/v1/chat/health` | Chat service health |
| GET | `/api/v1/documents/{path}` | Retrieve documents |
| GET | `/api/v1/health/` | Basic health check |
| GET | `/api/v1/health/liveness` | Kubernetes liveness probe |
| GET | `/api/v1/health/readiness` | Kubernetes readiness probe |
| GET | `/api/v1/health/detailed` | Detailed health with components |
| GET | `/api/v1/health/cache` | Cache statistics |
| POST | `/api/v1/health/cache/clear` | Clear all caches |

### Root Endpoints (Unversioned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Legacy health check |
| GET | `/metrics` | Performance metrics |
| POST | `/metrics/reset` | Reset metrics |
| GET | `/docs` | OpenAPI documentation |
| GET | `/redoc` | ReDoc documentation |

## Client Guidelines

### Version Selection

```typescript
// Recommended: Use environment variable
const API_VERSION = process.env.API_VERSION || 'v1';
const BASE_URL = `https://api.example.com/api/${API_VERSION}`;

// Or hardcode for stability
const BASE_URL = 'https://api.example.com/api/v1';
```

### Handling Deprecation

Monitor response headers for deprecation warnings:

```typescript
const response = await fetch(`${BASE_URL}/chat/stream`, options);

if (response.headers.get('Deprecation') === 'true') {
  const sunsetDate = response.headers.get('Sunset');
  console.warn(`API version deprecated. Sunset: ${sunsetDate}`);
}
```

### Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| 200-299 | Success | Process response |
| 400 | Bad Request | Fix request parameters |
| 401 | Unauthorized | Check authentication |
| 404 | Not Found | Check endpoint path |
| 410 | Gone | Version removed, upgrade |
| 429 | Rate Limited | Implement backoff |
| 500-599 | Server Error | Retry with backoff |

## Changelog

### v1.0.0 (Current)

- Initial stable release
- Chat streaming with RAG
- Document retrieval
- Comprehensive health checks
- Performance monitoring

## Contact

For API questions or migration assistance:
- Open an issue in the repository
- Check the `/docs` endpoint for OpenAPI spec
