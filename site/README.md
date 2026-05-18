# SafeClaw Site

Static product site for SafeClaw.

## Pages

- `index.html`: Landing page and product positioning.
- `install.html`: Quick install, guided install, Mac setup, Ollama, WhatsApp,
  and verification.
- `docs.html`: Commands, permissions, memory, WhatsApp, and project structure.
- `api.html`: CLI, tool, environment, webhook, and testing reference.
- `roadmap.html`: Roadmap, open safety questions, and contributor areas.

Support links point to:

```text
https://buymeacoffee.com/alifla
```

Community links point to:

```text
https://www.reddit.com/r/Safeclaw/
```

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

## Build

The committed `site/` files do not contain the Cloudflare Web Analytics token.
Build the deployable site into `site-dist/`:

```bash
bash scripts/build-site.sh
```

To inject Cloudflare Web Analytics during the build:

```bash
CF_WEB_ANALYTICS_TOKEN=your-token bash scripts/build-site.sh
```

`site-dist/` is ignored by git so the generated analytics snippet is not
committed.

## Deploy with Cloudflare Workers static assets

This repo includes `wrangler.jsonc` configured to deploy `site-dist/`.

Cloudflare build settings:

```text
Build command: bash scripts/build-site.sh
Deploy command: npx wrangler deploy
Root directory: /
```

Set this build environment variable in Cloudflare:

```text
CF_WEB_ANALYTICS_TOKEN=your-token
```

## Publish with GitHub Pages

1. Push this repo to GitHub.
2. Open repository Settings.
3. Go to Pages.
4. Set source to GitHub Actions or deploy the `site/` folder with your
   preferred static-site workflow.

The site has no build step and no npm dependencies.
