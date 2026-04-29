# Bloxp Revived — Plan de Desarrollo

Recreación moderna de [Bloxp](https://web.archive.org/web/20200812034023/http://www.bloxp.com/):
herramienta que convierte blogs completos en ebooks descargables (ePub, Mobi, PDF).

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS |
| Estado | Zustand (form) + React Query (server state) |
| Backend | Python + FastAPI |
| Jobs async | Celery + Redis |
| Feed parsing | feedparser |
| Web crawling | httpx + BeautifulSoup4 |
| Extracción contenido | trafilatura + python-readability (fallback) |
| ePub | ebooklib |
| Mobi | Calibre CLI (`ebook-convert`) |
| PDF | WeasyPrint |
| Dev environment | Docker Compose |

---

## EPICs

### EPIC 1 — Infraestructura y scaffold ✅
Estructura del monorepo, Docker Compose, configuración base.

- [x] Estructura de carpetas `frontend/` + `backend/`
- [x] `docker-compose.yml` con Redis + backend + worker + frontend
- [x] `.env.example`
- [x] `backend/Dockerfile`
- [x] `backend/requirements.txt`
- [x] `backend/config.py` (pydantic-settings)

---

### EPIC 2 — Backend: modelos y store ✅
Modelos Pydantic para jobs y opciones del formulario. Estado de jobs en Redis.

- [x] `models/job.py` — `JobState`, `JobStatus`, `JobStatusResponse`
- [x] `models/ebook_options.py` — `BasicJobRequest`, `AdvancedJobRequest`, `CustomSelector`
- [x] `storage/file_manager.py` — rutas de archivos generados, cleanup
- [x] `tasks/celery_app.py` — instancia Celery configurada

---

### EPIC 3 — Backend: servicios de procesamiento ✅
Pipeline completo: feed → crawl → extracción → generación de ebooks.

- [x] `services/feed_parser.py` — feedparser wrapper
- [x] `services/link_finder.py` — detección de "post anterior" (heurístico + selector custom)
- [x] `services/crawler.py` — httpx async, 5 concurrentes, crawl por feed o por URL
- [x] `services/content_extractor.py` — trafilatura + readability fallback
- [x] `services/epub_builder.py` — ebooklib, TOC opcional, links a footnotes
- [x] `services/mobi_converter.py` — Calibre CLI subprocess, manejo de error si no instalado
- [x] `services/pdf_builder.py` — WeasyPrint

---

### EPIC 4 — Backend: API y task pipeline ✅✅
Task Celery completo, endpoints FastAPI, rutas de descarga.

- [x] `tasks/process_blog.py` — tasks `process_basic` y `process_advanced`
- [x] `main.py` — FastAPI app, CORS, router registration
- [x] `routers/jobs.py` — `POST /api/jobs`, `GET /api/jobs/{id}`
- [x] `routers/download.py` — `GET /api/jobs/{id}/download/{format}`
- [x] `routers/contact.py` — `POST /api/contact`

---

### EPIC 5 — Frontend: scaffold y componentes UI ✅
Vite + React 19 + TypeScript + Tailwind. Componentes base reutilizables.

- [x] Scaffold Vite + dependencias (React Router, React Query, Zustand)
- [x] `components/layout/Header.tsx` — nav: Home | Advanced | About | FAQ
- [x] `components/layout/Footer.tsx`
- [x] `components/ui/Button.tsx`
- [x] `components/ui/Input.tsx`
- [x] `components/ui/Checkbox.tsx`
- [x] `components/ui/Fieldset.tsx`
- [x] `components/ui/ErrorPanel.tsx`
- [x] `components/ui/ProgressBar.tsx`
- [x] `components/ui/Spinner.tsx`
- [x] `components/forms/FormField.tsx`

---

### EPIC 6 — Frontend: páginas principales ✅
Páginas que replican la estructura visual del Bloxp original.

- [x] `stores/ebookStore.ts` — Zustand store (form fields + activeJobId)
- [x] `api/client.ts` — fetch wrappers tipados
- [x] `hooks/useJobStatus.ts` — React Query polling (2s, auto-stop)
- [x] `hooks/useSubmitJob.ts` — mutation hook
- [x] `pages/HomePage.tsx` — hero + BasicEbookForm + sección features + contacto
- [x] `components/forms/BasicEbookForm.tsx`
- [x] `pages/AdvancedConfigPage.tsx`
- [x] `components/forms/AdvancedEbookForm.tsx`
- [x] `components/forms/ExportSettingsSection.tsx` — toggle con customSearchOpt
- [x] `pages/WorkingPage.tsx` — progress bar, polling, botones de descarga
- [x] `pages/AboutPage.tsx`
- [x] `pages/FaqPage.tsx`

---

### EPIC 7 — Integración E2E y polish ✅
Prueba completa del flujo, dark mode, mobile responsiveness.

- [x] Error handling visible en UI (URL inválida, sin posts, timeout)
- [x] Dark mode (`dark:` Tailwind variants en todos los componentes)
- [x] Mobile-first responsive (Tailwind breakpoints sm/md)
- [x] Cleanup de jobs expirados — `tasks/cleanup.py` + Celery beat cada hora
- [x] Servicio `beat` en docker-compose
- [x] Redis healthcheck en docker-compose
- [x] Página `/contact` con formulario
- [x] Header: link Contact agregado
- [x] `routers/jobs.py` unificado — acepta `custom_selector` anidado del frontend

---

## Flujo de datos

```
User submits form
      │
      ▼
POST /api/jobs
      │
      ▼
Celery task enqueued → job_id returned
      │
      ▼
Frontend navega a /working/:job_id
      │
      ▼
React Query polling GET /api/jobs/:id (cada 2s)
      │
      ├─ status: crawling → progress bar update
      │
      └─ status: done → download buttons appear
                         (epub / mobi / pdf)
```

---

## Estructura de archivos generados

```
generated/
└── {job_id}/
    ├── output.epub
    ├── output.mobi   (si Calibre instalado)
    └── output.pdf
```

TTL: 24 horas. Cleanup automático via Celery beat (EPIC 7).
