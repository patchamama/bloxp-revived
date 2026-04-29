# Bloxp Revived

> **Convertí cualquier blog en un ebook descargable — ePub, Mobi o PDF.**

Una recreación moderna y open-source del [Bloxp](https://web.archive.org/web/20200812034023/http://www.bloxp.com/) original — una herramienta que desapareció de internet. Este proyecto la trae de vuelta con un stack contemporáneo, manteniendo su propósito original: darle una segunda vida a cualquier blog en formato portable y legible.

---

## La historia

El Bloxp original era una herramienta pequeña pero brillante. Pegabas la URL del feed RSS de un blog y, minutos después, tenías un archivo ePub o Mobi limpio con cada entrada que se había escrito — listo para leer en tu Kindle o e-reader. A diferencia de servicios similares que solo exportaban los posts más recientes, Bloxp recorría el archivo completo, desde la primera entrada hasta la última.

Desapareció de internet alrededor de 2020. Muchos de los blogs que ayudó a archivar también se fueron. Pero gracias a haber hecho conversiones con Bloxp antes de que desaparecieran, esas palabras todavía se pueden leer hoy — guardadas en silencio en archivos ePub en algún lugar.

Esta reimplementación estuvo pendiente durante mucho tiempo. Lo que finalmente lo hizo posible en unas pocas horas fue la aparición del desarrollo asistido por IA: una visión clara de lo que había que construir, y las herramientas para construirlo rápido.

> *Créditos y agradecimiento al proyecto Bloxp original y a su autor:*
> [bloxp.com/about](https://web.archive.org/web/20200812034023/http://www.bloxp.com/about.php)

📖 **[Read in English](README.md)**

---

## Funcionalidades

- **Exportación por feed** — pegá una URL RSS/Atom y exportá el archivo completo (hasta 250 posts)
- **Modo avanzado** — para blogs sin feed: proporcioná la URL del primer post y un selector CSS para navegar al "post anterior"
- **Tres formatos de salida** — ePub (universal), Mobi (Kindle vía Calibre), PDF (vía WeasyPrint)
- **Tabla de contenidos** — opcional, generada automáticamente a partir de los títulos de los posts
- **Links como notas al pie** — conversión opcional de links inline a notas numeradas
- **Procesamiento asíncrono** — los trabajos corren en background vía Celery; el progreso se trackea en tiempo real
- **Limpieza automática** — los archivos generados expiran después de 24 horas

---

## Arquitectura

```mermaid
graph TD
    User["👤 Usuario (Browser)"]

    subgraph Frontend["Frontend — React 19 + TypeScript + Vite"]
        Home["HomePage\n(BasicEbookForm)"]
        Advanced["AdvancedConfigPage\n(AdvancedEbookForm)"]
        Working["WorkingPage\n(polling cada 2s)"]
    end

    subgraph Backend["Backend — FastAPI (Python)"]
        API["POST /api/jobs\nGET /api/jobs/:id\nGET /api/jobs/:id/download/:fmt"]
        Static["Static files\n(React SPA en producción)"]
    end

    subgraph Queue["Cola de tareas — Celery + Redis"]
        Worker["Celery Worker\n(process_basic / process_advanced)"]
        Beat["Celery Beat\n(limpieza de jobs expirados cada hora)"]
        Redis[("Redis\n(broker + estado de jobs)")]
    end

    subgraph Pipeline["Pipeline de procesamiento"]
        FeedParser["feedparser\n(RSS/Atom)"]
        Crawler["httpx + BeautifulSoup4\n(crawl async, 5 concurrentes)"]
        Extractor["trafilatura\n(extracción de contenido)"]
        EPub["ebooklib\n(generación de ePub)"]
        Mobi["Calibre CLI\n(conversión a Mobi)"]
        PDF["WeasyPrint\n(generación de PDF)"]
    end

    User --> Home
    User --> Advanced
    Home -->|"POST /api/jobs"| API
    Advanced -->|"POST /api/jobs"| API
    Working -->|"GET /api/jobs/:id"| API
    API -->|"encola tarea"| Redis
    Redis --> Worker
    Worker --> FeedParser
    Worker --> Crawler
    Crawler --> Extractor
    Extractor --> EPub
    EPub --> Mobi
    EPub --> PDF
    Worker -->|"actualiza estado"| Redis
    Working -->|"descarga"| API
    Beat --> Redis
```

### Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19 + TypeScript + Vite + Tailwind CSS v4 |
| Estado | Zustand (formularios) + TanStack Query (estado del servidor) |
| Routing | React Router v7 |
| Backend | Python 3.12 + FastAPI |
| Cola de tareas | Celery 5 + Redis 7 |
| Parsing de feeds | feedparser |
| Web crawling | httpx (async) + BeautifulSoup4 |
| Extracción de contenido | trafilatura + python-readability (fallback) |
| Generación de ePub | ebooklib |
| Conversión a Mobi | Calibre CLI (`ebook-convert`) |
| Generación de PDF | WeasyPrint |
| Entorno de desarrollo | Docker Compose |

---

## Inicio rápido

### Opción A — Docker Compose (recomendado)

```bash
git clone https://github.com/patchamama/bloxp-revived.git
cd bloxp-revived
docker compose up --build
```

Abrí **http://localhost:5173**

### Opción B — Local (sin Docker)

**Requisitos previos:** Node.js ≥ 18, Python ≥ 3.11, Redis

```bash
# macOS
brew install redis node python
brew services start redis

# Clonar
git clone https://github.com/patchamama/bloxp-revived.git
cd bloxp-revived

# Build + deploy (un solo comando)
chmod +x deploy.sh
./deploy.sh
```

Abrí **http://localhost:8000**

Para detener todos los servicios:
```bash
./stop.sh
```

#### Flags de deploy.sh

| Flag | Descripción |
|------|-------------|
| `--no-build` | Omitir el build del frontend, reutilizar `frontend/dist/` existente |
| `--no-venv` | Omitir la creación del venv, asumir que ya existe |
| `--help` | Mostrar uso |

---

## Estructura del proyecto

```
bloxp-revived/
├── frontend/                  # React 19 SPA
│   └── src/
│       ├── pages/             # HomePage, AdvancedConfigPage, WorkingPage…
│       ├── components/        # Primitivos de UI + componentes de formulario
│       ├── hooks/             # useJobStatus, useSubmitJob
│       ├── stores/            # Zustand ebook store
│       └── api/               # Wrappers de fetch tipados
├── backend/                   # FastAPI + Celery
│   ├── main.py                # Entry point (sirve API + SPA en producción)
│   ├── routers/               # jobs, download, contact
│   ├── tasks/                 # process_blog (Celery), cleanup (beat)
│   ├── services/              # feed_parser, crawler, extractor, epub/mobi/pdf builders
│   ├── models/                # Modelos Pydantic (JobState, EbookOptions)
│   └── storage/               # Gestión de rutas de archivos
├── generated/                 # Ebooks de salida (auto-creado, gitignored)
├── logs/                      # Logs de servicios (auto-creado, gitignored)
├── deploy.sh                  # Script de deploy local en producción
├── stop.sh                    # Detener todos los servicios locales
├── docker-compose.yml         # Stack completo vía Docker
├── TODO.md                    # Roadmap y problemas conocidos
└── README.md                  # Documentación en inglés
```

---

## Desarrollo

```bash
# Backend (con hot reload)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Celery worker (terminal separada)
celery -A tasks.celery_app worker --loglevel=info

# Frontend (terminal separada)
cd frontend
npm install && npm run dev
```

El servidor de desarrollo de Vite proxea las peticiones `/api/*` a `http://localhost:8000`.

---

## Variables de entorno

Copiá `.env.example` a `backend/.env` y ajustá según necesites:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Cadena de conexión a Redis |
| `GENERATED_DIR` | `../generated` | Directorio para los ebooks de salida |
| `SMTP_HOST` | — | Servidor SMTP para el formulario de contacto (opcional) |
| `SMTP_PORT` | `587` | Puerto SMTP |
| `SMTP_USER` | — | Usuario SMTP |
| `SMTP_PASS` | — | Contraseña SMTP |

---

## Contribuir

Las pull requests son bienvenidas. Para cambios importantes, abrí un issue primero.
Mirá [TODO.md](TODO.md) para una lista de ideas y problemas conocidos.

---

## Licencia

MIT

---

## Agradecimientos

Este proyecto no existiría sin el **Bloxp** original de su autor anónimo.
Las librerías originales sobre las que fue construido están listadas en:
[bloxp.com/about](https://web.archive.org/web/20200812034023/http://www.bloxp.com/about.php)

La reconstrucción moderna se para sobre los hombros de:
feedparser · trafilatura · ebooklib · Calibre · WeasyPrint · FastAPI · Celery · React · Tailwind CSS · y muchos otros.
