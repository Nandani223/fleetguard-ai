export default function EmptyState({ title, body, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6 border border-dashed border-line rounded-xl bg-surface">
      <div className="w-10 h-10 rounded-full bg-surface-sunken flex items-center justify-center mb-4">
        <div className="w-2 h-2 rounded-full bg-ink-faint" />
      </div>
      <h3 className="font-semibold text-ink mb-1">{title}</h3>
      {body && <p className="text-sm text-ink-dim max-w-sm mb-4">{body}</p>}
      {action}
    </div>
  )
}
