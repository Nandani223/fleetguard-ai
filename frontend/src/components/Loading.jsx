export default function Loading({ label = 'Loading' }) {
  return (
    <div className="flex items-center gap-2 text-ink-dim text-sm py-8 justify-center">
      <span className="w-3.5 h-3.5 rounded-full border-2 border-brand border-t-transparent animate-spin" />
      {label}…
    </div>
  )
}
