"""
FormNest — Public Routes

Unauthenticated endpoints for form rendering, embedding, and public form sharing.
These routes do NOT require a JWT token, only a form_key.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import settings
from server.core.db import get_db_session
from server.exceptions import NotFoundError
from server.models.forms import Form
from server.schemas.public import EmbedSnippetResponse, PublicFormResponse

logger = logging.getLogger("formnest.api.public")

router = APIRouter(tags=["Public"])


# =============================================================================
# Public form schema — used by embed widgets, React components, CLI tools
# =============================================================================


@router.get("/f/{form_key}", response_model=PublicFormResponse)
async def get_public_form(
    form_key: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve a public form's schema and configuration.

    This endpoint is **unauthenticated** — any client with the `form_key` can
    fetch the form definition. Use this to render a form in your React app,
    CLI tool, or any custom frontend.

    Returns only the fields needed for rendering (no internal IDs or billing
    metadata are exposed).
    """
    result = await db.execute(
        select(Form).where(
            Form.form_key == form_key,
            Form.deleted_at.is_(None),
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise NotFoundError("Form not found")

    if not form.is_active:
        raise NotFoundError("Form is not accepting submissions")

    return PublicFormResponse(
        form_key=form.form_key,
        name=form.name,
        form_type=form.form_type,
        schema=form.schema,
        steps_config=form.steps_config,
        success_message=form.success_message,
        redirect_url=form.redirect_url,
        styling=form.styling,
        submit_url=f"/submit/{form.form_key}",
    )


# =============================================================================
# Embed snippet — returns JS/iframe integration code
# =============================================================================


@router.get("/embed/{form_key}", response_model=EmbedSnippetResponse)
async def get_embed_snippet(
    form_key: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get embed integration code for a form.

    Returns:
    - **iframe_snippet**: Drop-in `<iframe>` tag for any HTML page
    - **script_snippet**: Async `<script>` tag for the FormNest JS widget
    - **react_snippet**: Copy-paste JSX for React applications
    - **api_endpoint**: The REST endpoint to POST submissions to

    ### Quick Embed (HTML)
    ```html
    <iframe src="https://api.formnest.in/embed/{form_key}/iframe"
            width="100%" height="500" frameborder="0"></iframe>
    ```

    ### React
    ```jsx
    import FormNest from '@formnest/react';
    <FormNest formKey="{form_key}" />
    ```
    """
    result = await db.execute(
        select(Form).where(
            Form.form_key == form_key,
            Form.deleted_at.is_(None),
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        raise NotFoundError("Form not found")

    base_url = settings.CLIENT_URL.rstrip("/")
    api_base = settings.API_URL.rstrip("/")

    iframe_url = f"{api_base}/embed/{form_key}/iframe"
    submit_url = f"{api_base}/submit/{form_key}"

    iframe_snippet = (
        f'<iframe\n'
        f'  src="{iframe_url}"\n'
        f'  width="100%"\n'
        f'  height="600"\n'
        f'  frameborder="0"\n'
        f'  style="border: none; border-radius: 8px;"\n'
        f'  title="{form.name}"\n'
        f'></iframe>'
    )

    script_snippet = (
        f'<div id="formnest-{form_key}"></div>\n'
        f'<script\n'
        f'  src="{api_base}/static/embed.js"\n'
        f'  data-form-key="{form_key}"\n'
        f'  data-container="formnest-{form_key}"\n'
        f'  async\n'
        f'></script>'
    )

    react_snippet = (
        f'import {{ FormNest }} from \'@formnest/react\';\n\n'
        f'export default function MyPage() {{\n'
        f'  return (\n'
        f'    <FormNest\n'
        f'      formKey="{form_key}"\n'
        f'      onSuccess={{(id) => console.log(\'Submitted:\', id)}}\n'
        f'    />\n'
        f'  );\n'
        f'}}'
    )

    curl_snippet = (
        f'curl -X POST {submit_url} \\\n'
        f'  -H "Content-Type: application/json" \\\n'
        f'  -d \'{{"data": {{"email": "user@example.com", "name": "Alice"}}}}\''
    )

    return EmbedSnippetResponse(
        form_key=form_key,
        form_name=form.name,
        submit_url=submit_url,
        iframe_snippet=iframe_snippet,
        script_snippet=script_snippet,
        react_snippet=react_snippet,
        curl_snippet=curl_snippet,
    )


@router.get("/embed/{form_key}/iframe", response_class=HTMLResponse)
async def render_form_iframe(
    form_key: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Render a standalone HTML page suitable for iframe embedding.

    This page loads the form schema from the public API and renders a
    fully functional form using vanilla JavaScript — no external dependencies.
    """
    result = await db.execute(
        select(Form).where(
            Form.form_key == form_key,
            Form.deleted_at.is_(None),
        )
    )
    form = result.scalar_one_or_none()
    if not form:
        return HTMLResponse(
            content="<html><body><p>Form not found.</p></body></html>",
            status_code=404,
        )

    if not form.is_active:
        return HTMLResponse(
            content="<html><body><p>This form is no longer accepting submissions.</p></body></html>",
            status_code=410,
        )

    success_msg = form.success_message or "Thank you! Your response has been submitted."
    form_name = form.name

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{form_name}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f9fafb;
      min-height: 100vh;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding: 24px 16px;
    }}
    .form-card {{
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.06);
      padding: 32px 28px;
      width: 100%;
      max-width: 520px;
    }}
    h1 {{ font-size: 1.4rem; font-weight: 700; margin-bottom: 24px; color: #111; }}
    label {{ display: block; font-size: .85rem; font-weight: 600; color: #374151; margin-bottom: 4px; }}
    input, textarea, select {{
      width: 100%; padding: 9px 12px;
      border: 1px solid #d1d5db; border-radius: 6px;
      font-size: .95rem; margin-bottom: 16px;
      transition: border-color .15s;
      background: #fff;
    }}
    input:focus, textarea:focus, select:focus {{
      outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,.15);
    }}
    textarea {{ min-height: 100px; resize: vertical; }}
    button[type=submit] {{
      width: 100%; padding: 11px;
      background: #6366f1; color: #fff;
      border: none; border-radius: 6px;
      font-size: 1rem; font-weight: 600;
      cursor: pointer; transition: background .15s;
    }}
    button[type=submit]:hover {{ background: #4f46e5; }}
    button[type=submit]:disabled {{ background: #a5b4fc; cursor: not-allowed; }}
    .error {{ color: #dc2626; font-size: .8rem; margin-top: -12px; margin-bottom: 10px; }}
    .success {{
      text-align: center; padding: 24px;
      background: #ecfdf5; border-radius: 8px;
      color: #065f46; font-weight: 600;
    }}
    .req {{ color: #ef4444; }}
    .powered {{
      text-align: center; margin-top: 16px;
      font-size: .75rem; color: #9ca3af;
    }}
    .powered a {{ color: #6366f1; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="form-card">
    <h1 id="form-title">{form_name}</h1>
    <div id="form-container"></div>
  </div>

  <script>
    const FORM_KEY = "{form_key}";
    const SUBMIT_URL = "/submit/" + FORM_KEY;

    async function loadForm() {{
      try {{
        const res = await fetch("/f/" + FORM_KEY);
        if (!res.ok) throw new Error("Form not found");
        const form = await res.json();
        renderForm(form);
      }} catch (e) {{
        document.getElementById("form-container").innerHTML =
          "<p style='color:#dc2626'>Could not load form. Please try again later.</p>";
      }}
    }}

    function renderForm(form) {{
      const container = document.getElementById("form-container");
      const el = document.createElement("form");
      el.id = "fn-form";

      form.schema.forEach(field => {{
        const wrapper = document.createElement("div");
        const label = document.createElement("label");
        label.htmlFor = field.key;
        label.textContent = field.label;
        if (field.required) {{
          const req = document.createElement("span");
          req.className = "req"; req.textContent = " *";
          label.appendChild(req);
        }}
        wrapper.appendChild(label);

        let input;
        if (field.type === "textarea") {{
          input = document.createElement("textarea");
        }} else if (field.type === "select" && field.options) {{
          input = document.createElement("select");
          const blank = document.createElement("option");
          blank.value = ""; blank.textContent = field.placeholder || "Select…";
          input.appendChild(blank);
          field.options.forEach(opt => {{
            const o = document.createElement("option");
            o.value = opt; o.textContent = opt;
            input.appendChild(o);
          }});
        }} else if (field.type === "checkbox") {{
          input = document.createElement("input");
          input.type = "checkbox";
          input.style.width = "auto";
          input.style.marginRight = "8px";
        }} else {{
          input = document.createElement("input");
          input.type = field.type === "email" ? "email"
                      : field.type === "number" ? "number"
                      : field.type === "url"    ? "url"
                      : field.type === "date"   ? "date"
                      : field.type === "phone"  ? "tel"
                      : "text";
        }}

        input.id = field.key;
        input.name = field.key;
        if (field.placeholder) input.placeholder = field.placeholder;
        if (field.required) input.required = true;

        wrapper.appendChild(input);
        el.appendChild(wrapper);
      }});

      // Hidden honeypot
      const honey = document.createElement("input");
      honey.type = "text"; honey.name = "_gotcha";
      honey.style.display = "none"; honey.tabIndex = -1;
      el.appendChild(honey);

      const btn = document.createElement("button");
      btn.type = "submit"; btn.textContent = "Submit";
      el.appendChild(btn);

      el.addEventListener("submit", async (e) => {{
        e.preventDefault();
        btn.disabled = true; btn.textContent = "Submitting…";
        const formData = new FormData(el);
        const data = {{}};
        formData.forEach((v, k) => {{ data[k] = v; }});

        try {{
          const res = await fetch(SUBMIT_URL, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              data,
              metadata: {{
                source_url: window.location.href,
                referrer: document.referrer,
                started_at: window._fnStarted,
              }},
            }}),
          }});

          if (res.ok) {{
            container.innerHTML = '<div class="success">{success_msg}</div>' +
              '<p class="powered">Powered by <a href="https://formnest.in" target="_blank">FormNest</a></p>';
          }} else {{
            const err = await res.json();
            btn.disabled = false; btn.textContent = "Submit";
            const errEl = document.createElement("p");
            errEl.className = "error";
            errEl.textContent = err.detail || "Submission failed. Please try again.";
            btn.parentNode.insertBefore(errEl, btn);
          }}
        }} catch (err) {{
          btn.disabled = false; btn.textContent = "Submit";
          alert("Network error. Please try again.");
        }}
      }});

      container.appendChild(el);
      container.insertAdjacentHTML("beforeend",
        '<p class="powered">Powered by <a href="https://formnest.in" target="_blank">FormNest</a></p>');
    }}

    window._fnStarted = Date.now() / 1000;
    loadForm();
  </script>
</body>
</html>"""

    return HTMLResponse(content=html, status_code=200)
