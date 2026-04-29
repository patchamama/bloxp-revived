import type { ReactNode } from 'react'

interface FieldsetProps {
  legend: string
  children: ReactNode
}

export function Fieldset({ legend, children }: FieldsetProps) {
  return (
    <fieldset className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
      <legend className="px-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
        {legend}
      </legend>
      <div className="space-y-4 pt-1">{children}</div>
    </fieldset>
  )
}
