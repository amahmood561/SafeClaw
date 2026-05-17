# SafeClaw Site

Static product site for SafeClaw.

## Pages

- `index.html`: Landing page and product positioning.
- `install.html`: Quick install, guided install, Mac setup, Ollama, WhatsApp,
  and verification.
- `docs.html`: Commands, permissions, memory, WhatsApp, and project structure.
- `api.html`: CLI, tool, environment, webhook, and testing reference.
- `roadmap.html`: Roadmap, open safety questions, and contributor areas.

## Local preview

Open `index.html` directly in a browser, or run:

```bash
cd site
python3 -m http.server 8000
```

Then visit:

```text
http://localhost:8000
```

## Publish with GitHub Pages

1. Push this repo to GitHub.
2. Open repository Settings.
3. Go to Pages.
4. Set source to GitHub Actions or deploy the `site/` folder with your
   preferred static-site workflow.

The site has no build step and no npm dependencies.
