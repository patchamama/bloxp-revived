import { AdvancedEbookForm } from '@/components/forms/AdvancedEbookForm'

export function AdvancedConfigPage() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-12 space-y-10">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Advanced Configuration
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Use this form when your blog doesn't have a standard RSS feed, or when you want to crawl
          posts linked via a custom HTML navigation pattern.
        </p>
      </div>

      <AdvancedEbookForm />

      <section className="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200">
          Custom HTML selector examples
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          The crawler follows "previous post" links through your blog. Use the selector fields to
          tell it exactly which HTML element to look for.
        </p>
        <div className="space-y-4 text-sm">
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
            <p className="font-semibold text-gray-800 dark:text-gray-200">
              1. Standard <code className="font-mono text-blue-600 dark:text-blue-400">link rel=prev</code>
            </p>
            <code className="block text-xs bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-300 p-2 rounded font-mono">
              {'<link rel="prev" href="/older-post" />'}
            </code>
            <p className="text-gray-600 dark:text-gray-400">
              Tag: <code className="font-mono">link</code> · Attr name:{' '}
              <code className="font-mono">rel</code> · Attr value:{' '}
              <code className="font-mono">prev</code>
            </p>
          </div>

          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
            <p className="font-semibold text-gray-800 dark:text-gray-200">
              2. Anchor with CSS class
            </p>
            <code className="block text-xs bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-300 p-2 rounded font-mono">
              {'<a class="older-link" href="/older-post">Older</a>'}
            </code>
            <p className="text-gray-600 dark:text-gray-400">
              Tag: <code className="font-mono">a</code> · Attr name:{' '}
              <code className="font-mono">class</code> · Attr value:{' '}
              <code className="font-mono">older-link</code>
            </p>
          </div>

          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
            <p className="font-semibold text-gray-800 dark:text-gray-200">
              3. Relative URLs with prefix
            </p>
            <code className="block text-xs bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-300 p-2 rounded font-mono">
              {'<a rel="prev" href="/older-post">Older</a>'}
            </code>
            <p className="text-gray-600 dark:text-gray-400">
              Set <strong>URL prefix</strong> to{' '}
              <code className="font-mono">https://example.com</code> so relative hrefs become
              absolute.
            </p>
          </div>

          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2">
            <p className="font-semibold text-gray-800 dark:text-gray-200">
              4. Nested anchor inside a span
            </p>
            <code className="block text-xs bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-300 p-2 rounded font-mono">
              {'<span class="nav-prev"><a href="/older-post">Older</a></span>'}
            </code>
            <p className="text-gray-600 dark:text-gray-400">
              Tag: <code className="font-mono">span</code> · Attr name:{' '}
              <code className="font-mono">class</code> · Attr value:{' '}
              <code className="font-mono">nav-prev</code> · enable{' '}
              <strong>Use parent tag</strong>
            </p>
          </div>
        </div>
      </section>
    </main>
  )
}
