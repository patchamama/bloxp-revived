# Changelog

All notable changes to this project are documented in this file.

## 2026-05-02 — Last 10 commits summary (EN)

- **9dfa57f** — Added system status monitoring endpoint and footer diagnostics.
- **17cafcf** — Improved verse normalization, stripped noisy HTML attributes, and hardened PDF generation.
- **15a03ed** — Added video embed handling, removed social/share clutter, normalized `br`→`p`, and improved link labels.
- **5cdc7bf** — Fixed verse detection for Blogger poem layouts split per `div`.
- **5fb3a21** — Wrapped loose Blogger `br`-delimited text into semantic `<p>` paragraphs.
- **1455cac** — Improved EPUB typography (paragraph indent/margins) and removed CMS class noise.
- **c78eed5** — Fixed `_isolate_images` to avoid inserting wrappers outside `<body>` when root image nodes exist.
- **f74e506** — Added `Referer` header for image fetch and removed empty wrappers after failed downloads.
- **2345895** — Added minimum image-size filtering, original URL in footnotes, better verse `<br>` normalization, and image diagnostics script.
- **531ea01** — Added job queue management and multiple EPUB/PDF/verse/footnote quality improvements.

## 2026-05-02 — Resumen de los últimos 10 commits (ES)

- **9dfa57f** — Se agregó endpoint de estado del sistema y diagnóstico en el pie del frontend.
- **17cafcf** — Mejoras en normalización de verso, limpieza de atributos HTML y generación de PDF más robusta.
- **15a03ed** — Soporte de videos embebidos, limpieza de bloques sociales/compartir, normalización `br`→`p` y mejora de etiquetas de links.
- **5cdc7bf** — Corrección de detección de verso para poemas de Blogger divididos por `div`.
- **5fb3a21** — Se envolvió texto suelto delimitado por `br` en párrafos semánticos `<p>`.
- **1455cac** — Mejoras tipográficas en EPUB (sangría/márgenes) y limpieza de clases CMS.
- **c78eed5** — Corrección en `_isolate_images` para no insertar wrappers fuera de `<body>` cuando hay imágenes en raíz.
- **f74e506** — Se agregó header `Referer` al descargar imágenes y limpieza de wrappers vacíos tras fallos.
- **2345895** — Filtro de tamaño mínimo de imagen, URL original en notas al pie, mejor normalización de `<br>` en verso y script de diagnóstico de imágenes.
- **531ea01** — Se incorporó cola de trabajos y mejoras de calidad en EPUB/PDF/verso/tooltips de notas al pie.
