import type { FormEvent } from 'react'
import { useState } from 'react'
import { Input } from '@/components/ui/Input'
import { Checkbox } from '@/components/ui/Checkbox'
import { Button } from '@/components/ui/Button'
import { Fieldset } from '@/components/ui/Fieldset'
import { ErrorPanel } from '@/components/ui/ErrorPanel'
import { ExportSettingsSection } from './ExportSettingsSection'
import { useEbookStore } from '@/stores/ebookStore'
import { useSubmitAdvancedJob } from '@/hooks/useSubmitJob'

export function AdvancedEbookForm() {
  const {
    startingUrl,
    startingTitle,
    siteUrl,
    siteTitle,
    siteDescription,
    linksToFootnotes,
    addTOC,
    maxPosts,
    setField,
  } = useEbookStore()
  const [errors, setErrors] = useState<Record<string, string>>({})
  const mutation = useSubmitAdvancedJob()

  const validate = () => {
    const errs: Record<string, string> = {}
    if (!startingUrl.trim()) errs.startingUrl = 'Required'
    if (!startingTitle.trim()) errs.startingTitle = 'Required'
    if (!siteUrl.trim()) errs.siteUrl = 'Required'
    if (!siteTitle.trim()) errs.siteTitle = 'Required'
    return errs
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setErrors({})
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Fieldset legend="First Post">
        <Input
          id="startingUrl"
          label="URL of first post"
          type="url"
          placeholder="https://example.com/first-post"
          value={startingUrl}
          onChange={(e) => setField('startingUrl', e.target.value)}
          error={errors.startingUrl}
        />
        <Input
          id="startingTitle"
          label="Title of first post"
          placeholder="My First Post"
          value={startingTitle}
          onChange={(e) => setField('startingTitle', e.target.value)}
          error={errors.startingTitle}
        />
      </Fieldset>

      <Fieldset legend="Site Info">
        <Input
          id="siteUrl"
          label="Blog URL"
          type="url"
          placeholder="https://example.com"
          value={siteUrl}
          onChange={(e) => setField('siteUrl', e.target.value)}
          error={errors.siteUrl}
        />
        <Input
          id="siteTitle"
          label="Blog title"
          placeholder="My Awesome Blog"
          value={siteTitle}
          onChange={(e) => setField('siteTitle', e.target.value)}
          error={errors.siteTitle}
        />
        <Input
          id="siteDescription"
          label="Blog description (optional)"
          placeholder="A blog about..."
          value={siteDescription}
          onChange={(e) => setField('siteDescription', e.target.value)}
        />
      </Fieldset>

      <Fieldset legend="Ebook Options">
        <Input
          id="maxPosts"
          label="Maximum posts"
          type="number"
          min={1}
          max={500}
          value={maxPosts}
          onChange={(e) => setField('maxPosts', parseInt(e.target.value, 10) || 250)}
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
      </Fieldset>

      <Fieldset legend="Export Settings">
        <ExportSettingsSection />
      </Fieldset>

      {mutation.isError && (
        <ErrorPanel message="Failed to start job. Please check your inputs and try again." />
      )}
      <Button type="submit" loading={mutation.isPending} className="w-full">
        Convert to Ebook
      </Button>
    </form>
  )
}
