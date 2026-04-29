interface FaqItem {
  q: string
  a: string
}

const faqs: FaqItem[] = [
  {
    q: 'What kind of blogs are supported?',
    a: 'Any blog with a standard RSS or Atom feed. For blogs without feeds, use the Advanced configuration to point to the first post and let the crawler follow navigation links.',
  },
  {
    q: 'How many posts can I convert?',
    a: 'By default up to 250 posts. In Advanced mode you can set a custom maximum up to 500.',
  },
  {
    q: 'What ebook formats are available?',
    a: 'ePub (universal), Mobi (Kindle, requires Calibre on the server), and PDF.',
  },
  {
    q: 'How long does conversion take?',
    a: 'Typically 30 seconds to a few minutes depending on the number of posts and server load. The progress bar keeps you updated.',
  },
  {
    q: 'Can I send the ebook to my Kindle?',
    a: 'Yes. Download the Mobi file and send it to your Kindle email address, or use the Send-to-Kindle app with the EPUB file.',
  },
  {
    q: 'How long are ebooks available for download?',
    a: 'Generated ebooks are stored for 24 hours and then automatically deleted.',
  },
  {
    q: 'Is my blog URL stored or shared?',
    a: 'No. URLs and generated files are kept only during the job lifetime and are deleted after 24 hours. Nothing is shared.',
  },
]

export function FaqPage() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-12 space-y-8">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
        Frequently Asked Questions
      </h1>
      <dl className="space-y-7">
        {faqs.map(({ q, a }) => (
          <div key={q} className="space-y-1.5">
            <dt className="font-semibold text-gray-800 dark:text-gray-200">{q}</dt>
            <dd className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{a}</dd>
          </div>
        ))}
      </dl>
    </main>
  )
}
