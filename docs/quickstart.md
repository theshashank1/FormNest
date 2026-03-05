# FormNest API — Quick Start

FormNest lets you embed forms anywhere and collect submissions with zero backend code.
In five minutes you'll have a working form collecting real data.

---

## 1. Sign up and get your credentials

```bash
curl -X POST https://api.formnest.in/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "super-secret-password",
    "name": "Your Name"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "...",
  "expires_in": 604800
}
```

Save the `access_token` — you'll use it for all authenticated requests.

---

## 2. Create a project

```bash
curl -X POST https://api.formnest.in/api/v1/projects \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Website"}'
```

Note the `id` and `api_key` fields in the response.

---

## 3. Create a form

```bash
curl -X POST https://api.formnest.in/api/v1/projects/<project_id>/forms \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Contact Form",
    "schema": [
      {"key": "name",    "label": "Full Name",  "type": "text",  "required": true},
      {"key": "email",   "label": "Email",       "type": "email", "required": true},
      {"key": "message", "label": "Message",     "type": "textarea"}
    ]
  }'
```

Note the `form_key` in the response (e.g. `fm_a1b2c3d4e5f6`).

---

## 4. Collect a submission

Anyone — no login required — can POST to your form:

```bash
curl -X POST https://api.formnest.in/submit/<form_key> \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "Alice",
      "email": "alice@example.com",
      "message": "Hello!"
    }
  }'
```

---

## 5. Choose your integration

### React / Next.js
```jsx
import { useState, useEffect } from 'react';

export default function ContactForm({ formKey }) {
  const [schema, setSchema] = useState(null);
  const [status, setStatus] = useState('idle');

  useEffect(() => {
    fetch(`https://api.formnest.in/f/${formKey}`)
      .then(r => r.json())
      .then(setSchema);
  }, [formKey]);

  async function handleSubmit(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    setStatus('loading');
    const res = await fetch(`https://api.formnest.in/submit/${formKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data }),
    });
    setStatus(res.ok ? 'success' : 'error');
  }

  if (status === 'success') return <p>Thank you!</p>;
  if (!schema) return <p>Loading…</p>;

  return (
    <form onSubmit={handleSubmit}>
      {schema.schema.map(field => (
        <div key={field.key}>
          <label>{field.label}</label>
          <input name={field.key} type={field.type} required={field.required} />
        </div>
      ))}
      <button type="submit" disabled={status === 'loading'}>Submit</button>
    </form>
  );
}
```

### HTML iframe (zero code)
```html
<iframe
  src="https://api.formnest.in/embed/<form_key>/iframe"
  width="100%"
  height="600"
  frameborder="0"
  style="border: none; border-radius: 8px;"
  title="Contact Form"
></iframe>
```

### CLI / Shell script
```bash
#!/usr/bin/env bash
FORM_KEY="fm_a1b2c3d4e5f6"
curl -s -X POST "https://api.formnest.in/submit/$FORM_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"data\": {\"email\": \"$(git config user.email)\", \"message\": \"Deploy complete\"}}"
```

---

## 6. View submissions

```bash
curl https://api.formnest.in/api/v1/projects/<project_id>/forms/<form_id>/submissions \
  -H "Authorization: Bearer <access_token>"
```

Or use your **API key** (great for server-side scripts):

```bash
curl https://api.formnest.in/api/v1/projects/<project_id>/forms/<form_id>/submissions \
  -H "X-API-Key: fn_<your_api_key>"
```

---

## Next steps

| Topic | Guide |
|-------|-------|
| Auth flows (JWT + API keys) | [auth.md](./auth.md) |
| Full form management API | [forms.md](./forms.md) |
| Submission API & filtering | [submissions.md](./submissions.md) |
| Embedding (React, iframe, vanilla) | [embed.md](./embed.md) |
| CLI & server-to-server integration | [cli.md](./cli.md) |
| Security (CORS, rate limits, spam) | [security.md](./security.md) |
