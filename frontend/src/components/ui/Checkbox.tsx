import type { InputHTMLAttributes } from 'react'

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string
}

export function Checkbox({ label, id, className = '', ...props }: CheckboxProps) {
  return (
    <label
      htmlFor={id}
      className={`flex items-center gap-2 cursor-pointer text-sm text-gray-700 dark:text-gray-300 ${className}`}
    >
      <input
        type="checkbox"
        id={id}
        {...props}
        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800"
      />
      {label}
    </label>
  )
}
