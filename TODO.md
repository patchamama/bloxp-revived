# TODO — Bloxp Revived

A living list of improvements, bugs, and ideas. Contributions welcome.

---

## 🐛 Known Issues

- [ ] Mobi output requires Calibre installed on the server; no graceful in-UI warning when unavailable
- [ ] Feed URLs that redirect to a login wall fail silently (no error surfaced to user)
- [ ] Very large blogs (500+ posts) may hit memory pressure in a single Celery task — needs chunking
- [ ] PDF output lacks chapter page-break support for very long posts

---

## 🚀 Features

### Core
- [ ] **Kindle Send**: direct "Send to Kindle" button using Amazon's email API
- [ ] **Cover image**: auto-generate ebook cover with blog title and avatar/logo
- [ ] **Custom CSS for ebooks**: let users inject custom styles into ePub/PDF output
- [ ] **Chapter ordering**: option to export newest-first or oldest-first
- [ ] **Date range filter**: export only posts published between two dates
- [ ] **Tag/category filter**: export only posts matching a given tag (RSS `<category>`)
- [ ] **Post preview**: show a list of discovered posts before generating the ebook
- [ ] **Re-export**: allow re-running a completed job without filling the form again

### Advanced
- [ ] **Sitemap.xml support**: use sitemap as an alternative to feed + next-post crawling
- [ ] **Authenticated blogs**: support Basic Auth or cookie-based sessions for private blogs
- [ ] **Image inlining**: download and embed remote images into ePub (currently linked)
- [ ] **Multi-language readability**: improve content extraction accuracy for non-English blogs

---

## 🏗️ Infrastructure

- [ ] **SSE progress**: replace polling with Server-Sent Events for real-time progress
- [ ] **S3 storage**: swap local `generated/` folder for S3 pre-signed URLs (production scaling)
- [ ] **Rate limiting**: add per-IP rate limiting to `POST /api/jobs` to prevent abuse
- [ ] **Job queue dashboard**: expose Flower or a simple admin UI for Celery monitoring
- [ ] **Docker multi-stage build**: slim production images (separate build/runtime stages)
- [ ] **Nginx config**: sample `nginx.conf` for reverse proxy in front of uvicorn
- [ ] **Health endpoint**: extend `/api/health` to include Redis and Celery worker status

---

## 🧪 Testing

- [ ] **Unit tests**: services (feed_parser, link_finder, content_extractor)
- [ ] **Integration tests**: full job pipeline with a real test blog
- [ ] **Frontend tests**: Vitest + React Testing Library for form validation and WorkingPage
- [ ] **E2E tests**: Playwright smoke test (submit → working → download)

---

## 📖 Documentation

- [ ] **API reference**: expand OpenAPI docs with examples for each endpoint
- [ ] **Deployment guide**: step-by-step VPS deploy (Nginx + systemd services)
- [ ] **Contributing guide**: `CONTRIBUTING.md` with branch strategy and PR checklist

---

## 🎨 UI / UX

- [ ] **Post count badge**: show estimated total posts found before crawl begins
- [ ] **Cancel job**: allow users to cancel a running job mid-crawl
- [ ] **Download expiry warning**: show countdown until generated files expire (24h)
- [ ] **Accessibility audit**: WCAG 2.1 AA pass for all interactive elements
- [ ] **PWA**: add service worker so the app works offline after first load

---

_Last updated: 2026-04-29_
