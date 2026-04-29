import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { HomePage } from '@/pages/HomePage'
import { AdvancedConfigPage } from '@/pages/AdvancedConfigPage'
import { WorkingPage } from '@/pages/WorkingPage'
import { AboutPage } from '@/pages/AboutPage'
import { FaqPage } from '@/pages/FaqPage'
import { ContactPage } from '@/pages/ContactPage'
import { HistoryPage } from '@/pages/HistoryPage'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col bg-white dark:bg-gray-900">
          <Header />
          <div className="flex-1">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/advanced" element={<AdvancedConfigPage />} />
              <Route path="/working/:jobId" element={<WorkingPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/faq" element={<FaqPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/history" element={<HistoryPage />} />
            </Routes>
          </div>
          <Footer />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
