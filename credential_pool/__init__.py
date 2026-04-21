"""
Provider Credential Pool + Auto-Rotating - Inspired by OpenClaude Issue #780.
Manages multiple API keys per provider with automatic rotation on:
- Rate limit (429) errors
- Authentication failures (401/403)
- Quota exhaustion
- Cooldown tracking
"""
