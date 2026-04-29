interface ErrorPanelProps {
  message: string
}

export function ErrorPanel({ message }: ErrorPanelProps) {
  return (
    <div className="rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 text-sm text-red-700 dark:text-red-300">
      {message}
    </div>
  )
}
