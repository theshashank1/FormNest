"""
FormNest — Public-Facing Schemas

Response models for unauthenticated public endpoints (form rendering, embed).
These schemas expose only what's safe to share publicly — no internal IDs,
billing metadata, or sensitive configuration.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PublicFormResponse(BaseModel):
    """
    Minimal form definition returned to unauthenticated clients.

    Used by embed widgets, React components, and CLI tools to render the form
    and know where to POST submissions.
    """

    form_key: str
    name: str
    form_type: str
    form_schema: list[dict[str, Any]]
    steps_config: dict[str, Any] | None = None
    success_message: str | None = None
    redirect_url: str | None = None
    styling: dict[str, Any] | None = None
    submit_url: str


class EmbedSnippetResponse(BaseModel):
    """
    Integration snippets returned by the embed endpoint.

    Contains ready-to-use code for HTML iframe, script tag, React JSX,
    and curl for CLI usage.
    """

    form_key: str
    form_name: str
    submit_url: str
    iframe_snippet: str
    script_snippet: str
    react_snippet: str
    curl_snippet: str
