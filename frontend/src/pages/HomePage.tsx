import { Link } from 'react-router-dom'
import { BasicEbookForm } from '@/components/forms/BasicEbookForm'

const features = [
  {
    title: 'Easy to use',
    description:
      'Just paste your blog feed URL and we handle the rest. No account needed.',
  },
  {
    title: 'Clean results',
    description:
      'Content is extracted and cleaned for an optimal reading experience on any device.',
  },
  {
    title: 'Standardized',
    description:
      'Download in ePub, Mobi, or PDF — compatible with Kindle, Kobo, and more.',
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
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-3 gap-10">
            {features.map((f) => (
              <div key={f.title} className="text-center space-y-2">
                <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                  {f.title}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
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
