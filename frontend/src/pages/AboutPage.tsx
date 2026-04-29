const originalLibraries = [
  '960 Grid System',
  'Arc90 Readability',
  'Font Awesome',
  'Goodlife FCT template',
  'HTML Purifier',
  'IcoMoon',
  'jQuery',
  'jqTransform',
  'jQuery UI Bootstrap',
  'normalize.css',
  'PHPePub',
  'PHPMailer',
  'phpMobi',
  'SimplePie',
]

export function AboutPage() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-12 space-y-10">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">About</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Bloxp Revived is a modern open-source recreation of the original{' '}
          <a
            href="https://web.archive.org/web/20200812034023/http://www.bloxp.com/"
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 dark:text-blue-400 hover:underline"
          >
            Bloxp
          </a>{' '}
          blog-to-ebook converter.
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
          Original Bloxp — Third-Party Libraries
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          The original Bloxp was built with the following open-source libraries:
        </p>
        <ul className="grid grid-cols-2 gap-y-1.5 gap-x-4 text-sm text-gray-700 dark:text-gray-300">
          {originalLibraries.map((lib) => (
            <li key={lib} className="flex items-center gap-2">
              <span className="text-blue-400 select-none">•</span>
              {lib}
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3 bg-blue-50 dark:bg-blue-950 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-blue-800 dark:text-blue-200">
          This modern rebuild uses different libraries:
        </h2>
        <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1.5">
          <li>React 19 + TypeScript + Vite + Tailwind CSS v4</li>
          <li>FastAPI + Celery + Redis (Python backend)</li>
          <li>feedparser · httpx · BeautifulSoup4 (feed parsing &amp; crawling)</li>
          <li>trafilatura · python-readability (content extraction)</li>
          <li>ebooklib (ePub) · Calibre CLI (Mobi) · WeasyPrint (PDF)</li>
          <li>Zustand · TanStack Query (frontend state management)</li>
          <li>React Router v7</li>
        </ul>
      </section>
    </main>
  )
}
