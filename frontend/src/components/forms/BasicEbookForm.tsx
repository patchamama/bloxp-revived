import type { FormEvent } from 'react'
import { useState } from 'react'
import { Input } from '@/components/ui/Input'
import { Checkbox } from '@/components/ui/Checkbox'
import { Button } from '@/components/ui/Button'
import { ErrorPanel } from '@/components/ui/ErrorPanel'
import { useEbookStore } from '@/stores/ebookStore'
import { useSubmitBasicJob } from '@/hooks/useSubmitJob'

export function BasicEbookForm() {
  const { feedUrl, linksToFootnotes, addTOC, setField } = useEbookStore()
  const [validationError, setValidationError] = useState('')
  const mutation = useSubmitBasicJob()

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!feedUrl.trim()) {
      setValidationError('Please enter a feed URL')
      return
    }
    setValidationError('')
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        id="feedUrl"
        label="Blog Feed URL (RSS or Atom)"
        type="url"
        placeholder="https://example.com/feed"
        value={feedUrl}
        onChange={(e) => setField('feedUrl', e.target.value)}
        error={validationError}
      />
      <div className="flex flex-wrap gap-6">
        <Checkbox
          id="linksToFootnotes"
          label="Convert links to footnotes"
          checked={linksToFootnotes}
          onChange={(e) => setField('linksToFootnotes', e.target.checked)}
        />
        <Checkbox
          id="addTOC"
          label="Add table of contents"
          checked={addTOC}
          onChange={(e) => setField('addTOC', e.target.checked)}
        />
      </div>
      {mutation.isError && (
        <ErrorPanel message="Failed to start job. Please check the URL and try again." />
      )}
      <Button type="submit" loading={mutation.isPending} className="w-full">
        Convert to Ebook
      </Button>
    </form>
  )
}
