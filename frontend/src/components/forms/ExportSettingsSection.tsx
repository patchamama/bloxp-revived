import { Checkbox } from '@/components/ui/Checkbox'
import { Input } from '@/components/ui/Input'
import { useEbookStore } from '@/stores/ebookStore'

export function ExportSettingsSection() {
  const { customSearchOpt, tagName, attrName, attrValue, preString, parentTag, setField } =
    useEbookStore()

  return (
    <div className="space-y-4">
      <Checkbox
        id="customSearchOpt"
        label="Use custom link selector"
        checked={customSearchOpt}
        onChange={(e) => setField('customSearchOpt', e.target.checked)}
      />
      {customSearchOpt && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-5 border-l-2 border-blue-200 dark:border-blue-800 ml-1">
          <Input
            id="tagName"
            label="Tag name"
            placeholder="a"
            value={tagName}
            onChange={(e) => setField('tagName', e.target.value)}
          />
          <Input
            id="attrName"
            label="Attribute name"
            placeholder="rel"
            value={attrName}
            onChange={(e) => setField('attrName', e.target.value)}
          />
          <Input
            id="attrValue"
            label="Attribute value"
            placeholder="prev"
            value={attrValue}
            onChange={(e) => setField('attrValue', e.target.value)}
          />
          <Input
            id="preString"
            label="URL prefix"
            placeholder="https://example.com"
            value={preString}
            onChange={(e) => setField('preString', e.target.value)}
          />
          <div className="col-span-full">
            <Checkbox
              id="parentTag"
              label="Use parent tag"
              checked={parentTag}
              onChange={(e) => setField('parentTag', e.target.checked)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
