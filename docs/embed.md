# Embedding Forms

FormNest provides multiple ways to embed a form in any website or app.
All embedding options are built on the same public endpoints — no authentication required.

---

## Public endpoints used for embedding

| Endpoint | Returns | Auth |
|----------|---------|------|
| `GET /f/{form_key}` | Form schema (JSON) | None |
| `GET /embed/{form_key}` | Integration code snippets | None |
| `GET /embed/{form_key}/iframe` | Full HTML page | None |
| `POST /submit/{form_key}` | Submit form data | None |

---

## 1. HTML iframe (zero code required)

Drop this into any HTML page — no JavaScript, no dependencies:

```html
<iframe
  src="https://api.formnest.in/embed/fm_a1b2c3d4e5f6/iframe"
  width="100%"
  height="600"
  frameborder="0"
  style="border: none; border-radius: 8px;"
  title="Contact Form"
></iframe>
```

The iframe page:
- Fetches the form schema automatically
- Renders all field types (text, email, select, textarea, checkbox, etc.)
- Handles spam protection (honeypot, timing)
- Shows your custom success message on submit
- Is fully responsive

### Get the iframe snippet via API

```bash
curl https://api.formnest.in/embed/fm_a1b2c3d4e5f6
```

```json
{
  "form_key": "fm_a1b2c3d4e5f6",
  "form_name": "Contact Form",
  "submit_url": "https://api.formnest.in/submit/fm_a1b2c3d4e5f6",
  "iframe_snippet": "<iframe src=\"...\" ...></iframe>",
  "script_snippet": "<div id=\"...\"> <script ...></script>",
  "react_snippet": "import { FormNest } from '@formnest/react';\n...",
  "curl_snippet": "curl -X POST ..."
}
```

---

## 2. React / Next.js

### Minimal implementation

```tsx
import { useState, useEffect, FormEvent } from 'react';

interface FormField {
  key: string;
  label: string;
  type: string;
  required?: boolean;
  placeholder?: string;
  options?: string[];
}

interface FormSchema {
  form_key: string;
  name: string;
  schema: FormField[];
  success_message?: string;
  submit_url: string;
}

export function FormNestForm({ formKey }: { formKey: string }) {
  const [schema, setSchema] = useState<FormSchema | null>(null);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`https://api.formnest.in/f/${formKey}`)
      .then(r => r.json())
      .then(setSchema)
      .catch(() => setError('Failed to load form'));
  }, [formKey]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus('loading');
    const data = Object.fromEntries(new FormData(e.currentTarget));

    const res = await fetch(`https://api.formnest.in/submit/${formKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data,
        metadata: { source_url: window.location.href },
      }),
    });

    if (res.ok) {
      setStatus('success');
    } else {
      const body = await res.json();
      setError(body.detail ?? 'Submission failed');
      setStatus('error');
    }
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!schema) return <p>Loading form…</p>;
  if (status === 'success') return <p>{schema.success_message ?? 'Thank you!'}</p>;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-xl font-bold">{schema.name}</h2>
      {schema.schema.map(field => (
        <div key={field.key}>
          <label htmlFor={field.key} className="block text-sm font-medium">
            {field.label} {field.required && <span className="text-red-500">*</span>}
          </label>
          {field.type === 'textarea' ? (
            <textarea
              id={field.key}
              name={field.key}
              required={field.required}
              placeholder={field.placeholder}
              className="mt-1 block w-full rounded border px-3 py-2"
            />
          ) : field.type === 'select' && field.options ? (
            <select id={field.key} name={field.key} required={field.required}
                    className="mt-1 block w-full rounded border px-3 py-2">
              <option value="">Select…</option>
              {field.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          ) : (
            <input
              id={field.key}
              name={field.key}
              type={field.type}
              required={field.required}
              placeholder={field.placeholder}
              className="mt-1 block w-full rounded border px-3 py-2"
            />
          )}
        </div>
      ))}
      {/* Honeypot — do not remove */}
      <input type="text" name="_gotcha" style={{ display: 'none' }} tabIndex={-1} />
      <button
        type="submit"
        disabled={status === 'loading'}
        className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {status === 'loading' ? 'Submitting…' : 'Submit'}
      </button>
      {status === 'error' && <p className="text-red-600 text-sm">{error}</p>}
    </form>
  );
}
```

### Next.js App Router (Server Component + Client Form)

```tsx
// app/contact/page.tsx
import { FormNestForm } from '@/components/FormNestForm';

export default function ContactPage() {
  return (
    <main className="max-w-lg mx-auto py-12 px-4">
      <FormNestForm formKey="fm_a1b2c3d4e5f6" />
    </main>
  );
}
```

---

## 3. Vanilla JavaScript

```html
<!DOCTYPE html>
<html>
<body>
  <div id="my-form"></div>
  <script>
    const FORM_KEY = 'fm_a1b2c3d4e5f6';
    const API = 'https://api.formnest.in';

    fetch(`${API}/f/${FORM_KEY}`)
      .then(r => r.json())
      .then(schema => {
        const form = document.createElement('form');

        schema.schema.forEach(field => {
          const label = document.createElement('label');
          label.textContent = field.label;
          const input = document.createElement('input');
          input.name = field.key;
          input.type = field.type;
          if (field.required) input.required = true;
          form.append(label, input, document.createElement('br'));
        });

        const btn = document.createElement('button');
        btn.type = 'submit';
        btn.textContent = 'Submit';
        form.append(btn);

        form.addEventListener('submit', async e => {
          e.preventDefault();
          const data = Object.fromEntries(new FormData(form));
          const res = await fetch(`${API}/submit/${FORM_KEY}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data }),
          });
          if (res.ok) {
            form.innerHTML = '<p>' + (schema.success_message || 'Thank you!') + '</p>';
          }
        });

        document.getElementById('my-form').append(form);
      });
  </script>
</body>
</html>
```

---

## 4. Styling the form

Pass custom styles when creating/updating a form:

```json
{
  "styling": {
    "primary_color": "#6366f1",
    "background": "#ffffff",
    "border_radius": "8px",
    "font_family": "Inter, sans-serif"
  }
}
```

The iframe renderer picks up these values automatically.
For React/vanilla JS, use them to style your own components.

---

## CORS note

The submission endpoint (`POST /submit/{form_key}`) accepts requests from **any
origin** by default.

To restrict which websites can submit to your form, configure `allowed_origins`:

```bash
curl -X PATCH https://api.formnest.in/api/v1/projects/<pid>/forms/<fid> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"allowed_origins": ["https://mysite.com"]}'
```

See [security.md](./security.md) for more details.
