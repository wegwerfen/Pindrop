export default function LoadingCard() {
  return (
    <div className="mb-4 rounded-lg border border-border bg-card overflow-hidden">
      <div className="h-14 bg-muted animate-pulse" />
      <div className="p-3 space-y-2">
        <div className="h-3 bg-muted animate-pulse rounded w-3/4" />
        <div className="h-3 bg-muted animate-pulse rounded w-1/2" />
        <div className="h-2 bg-muted animate-pulse rounded w-1/3 mt-1" />
      </div>
    </div>
  )
}
