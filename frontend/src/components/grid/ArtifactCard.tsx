import { formatDistanceToNow } from 'date-fns'
import { useSearchParams } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { getPluginMeta } from '@/lib/pluginRegistry'
import type { Artifact } from '@/types/artifact'

interface ArtifactCardProps {
  artifact: Artifact
}

export default function ArtifactCard({ artifact }: ArtifactCardProps) {
  const [, setSearchParams] = useSearchParams()
  const plugin = getPluginMeta(artifact.plugin_type)
  const Icon = plugin.Icon
  const hasThumbnail = artifact.thumbnail_path !== null

  const handleClick = () => {
    // Prep for Step 8 detail overlay — sets /?artifact=id
    setSearchParams({ artifact: artifact.id })
  }

  return (
    <div
      onClick={handleClick}
      className="mb-4 rounded-lg border border-border bg-card text-card-foreground overflow-hidden cursor-pointer hover:border-primary/40 hover:shadow-md transition-all duration-200"
    >
      {/* Hero: thumbnail or plugin icon */}
      {hasThumbnail ? (
        <div className="overflow-hidden bg-muted">
          <img
            src={`/api/artifacts/${artifact.id}/files/thumbnail`}
            alt={artifact.title}
            className="w-full object-cover"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.parentElement!.style.display = 'none'
            }}
          />
        </div>
      ) : (
        <div
          className="flex items-center justify-center h-14"
          style={{ backgroundColor: plugin.accent + '22' }}
        >
          <Icon size={24} style={{ color: plugin.accent }} />
        </div>
      )}

      {/* Body */}
      <div className="p-3 space-y-1.5">
        <h3 className="text-sm font-medium leading-snug line-clamp-2">{artifact.title}</h3>

        {artifact.excerpt && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {artifact.excerpt}
          </p>
        )}

        <div className="flex items-center justify-between gap-2 pt-0.5">
          <span className="text-xs text-muted-foreground truncate">
            {artifact.source_domain ?? plugin.label}
          </span>
          <span className="text-xs text-muted-foreground flex-shrink-0">
            {formatDistanceToNow(new Date(artifact.captured_at), { addSuffix: true })}
          </span>
        </div>

        {artifact.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-0.5">
            {artifact.tags.slice(0, 4).map((tag) => (
              <Badge
                key={tag.id}
                variant="secondary"
                className="text-xs px-1.5 py-0 h-4"
                style={tag.color ? { color: tag.color } : undefined}
              >
                {tag.name}
              </Badge>
            ))}
            {artifact.tags.length > 4 && (
              <Badge variant="secondary" className="text-xs px-1.5 py-0 h-4">
                +{artifact.tags.length - 4}
              </Badge>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
