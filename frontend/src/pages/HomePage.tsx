import { Link } from 'react-router-dom'
import { BasicEbookForm } from '@/components/forms/BasicEbookForm'

const features = [
  {
    title: 'Easy to use',
    description: 'Just paste your blog feed URL and we handle the rest. No account needed.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
      </svg>
    ),
  },
  {
    title: 'Clean results',
    description: 'Content is extracted and cleaned for an optimal reading experience on any device.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
      </svg>
    ),
  },
  {
    title: 'Standardized',
    description: 'Download in ePub, Mobi, or PDF — compatible with Kindle, Kobo, and more.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
    ),
  },
]

export function HomePage() {
  return (
    <main>
      <section className="bg-white dark:bg-gray-900 py-16 px-4">
        <div className="max-w-2xl mx-auto text-center space-y-6">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white tracking-tight">
            Convert your blog into an ebook
          </h1>
          <p className="text-lg text-gray-500 dark:text-gray-400">
            Turn any RSS or Atom blog feed into a downloadable ebook in seconds. Read your
            favourite blogs offline on Kindle, Kobo, or any e-reader.
          </p>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 text-left">
            <BasicEbookForm />
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Need more control?{' '}
            <Link
              to="/advanced"
              className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
            >
              Advanced configuration
            </Link>
          </p>
        </div>
      </section>

      <section className="bg-gray-50 dark:bg-gray-800 py-16 px-4">
        <div className="max-w-4xl mx-auto space-y-10">
          <div className="grid md:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-6 flex flex-col gap-4 hover:shadow-md transition-shadow"
              >
                <div className="text-blue-500 dark:text-blue-400">
                  {f.icon}
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">
                    {f.title}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                    {f.description}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <p className="text-center text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
            Bloxp is completely free to use. Need inspiration? Start creating your own{' '}
            <span className="text-gray-700 dark:text-gray-300 font-medium">stories compilation</span>,{' '}
            <span className="text-gray-700 dark:text-gray-300 font-medium">travel guide</span>,{' '}
            <span className="text-gray-700 dark:text-gray-300 font-medium">cooking recipes book</span>...
          </p>
        </div>
      </section>

      <section className="bg-blue-50 dark:bg-blue-950 py-14 px-4">
        <div className="max-w-2xl mx-auto text-center space-y-3">
          <h2 className="text-xl font-semibold text-blue-800 dark:text-blue-200">
            Share your reading list
          </h2>
          <p className="text-sm text-blue-700 dark:text-blue-300 leading-relaxed">
            Love a blog? Convert it and share the ebook with friends. Have questions or
            feedback?{' '}
            <Link to="/faq" className="underline font-medium">
              Check the FAQ
            </Link>{' '}
            or visit the{' '}
            <Link to="/about" className="underline font-medium">
              About page
            </Link>
            .
          </p>
        </div>
      </section>
    </main>
  )
}
