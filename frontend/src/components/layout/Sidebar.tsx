import { Moon, Sun, Pin, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { useTags } from '@/hooks/useTags'
import { useCollections } from '@/hooks/useCollections'
import { useFilterStore } from '@/store/filterStore'
import type { SortOption } from '@/lib/api'

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'captured_at_desc', label: 'Newest first' },
  { value: 'captured_at_asc',  label: 'Oldest first' },
  { value: 'title_asc',        label: 'Title A–Z' },
  { value: 'importance_desc',  label: 'Most important' },
]

interface SidebarProps {
  isDark: boolean
  onToggleDark: () => void
}

export default function Sidebar({ isDark, onToggleDark }: SidebarProps) {
  const { data: tags = [] }        = useTags()
  const { data: collections = [] } = useCollections()
  const {
    searchQuery, setSearchQuery,
    selectedTagId, setSelectedTagId,
    selectedCollectionId, setSelectedCollectionId,
    sort, setSort,
    clearFilters,
  } = useFilterStore()

  const hasActiveFilter = !!(selectedTagId || selectedCollectionId || searchQuery)

  return (
    <aside className="w-60 flex-shrink-0 border-r border-border flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <Pin size={18} className="text-primary" />
          <span className="font-semibold text-base tracking-tight">Pindrop</span>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onToggleDark}>
          {isDark ? <Sun size={14} /> : <Moon size={14} />}
        </Button>
      </div>

      <Separator />

      {/* Search */}
      <div className="px-3 pt-3 pb-2">
        <Input
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-8 text-sm"
        />
      </div>

      {/* Sort */}
      <div className="px-3 pb-3">
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortOption)}
          className="w-full text-xs rounded-md border border-input bg-background px-2 py-1.5 text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <Separator />

      <ScrollArea className="flex-1 py-2 px-2">
        {/* Collections */}
        {collections.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-2 mb-1">
              Collections
            </p>
            {collections.map((c) => (
              <button
                key={c.id}
                onClick={() =>
                  setSelectedCollectionId(selectedCollectionId === c.id ? null : c.id)
                }
                className={`w-full text-left px-2 py-1.5 rounded-md text-sm flex items-center justify-between hover:bg-accent transition-colors ${
                  selectedCollectionId === c.id ? 'bg-accent font-medium' : ''
                }`}
              >
                <span className="truncate">{c.name}</span>
                <span className="text-xs text-muted-foreground ml-1 flex-shrink-0">
                  {c.artifact_count}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-2 mb-1.5">
              Tags
            </p>
            <div className="flex flex-wrap gap-1 px-1">
              {tags.map((tag) => (
                <Badge
                  key={tag.id}
                  variant={selectedTagId === tag.id ? 'default' : 'outline'}
                  className="cursor-pointer text-xs py-0 h-5"
                  style={tag.color && selectedTagId !== tag.id ? { borderColor: tag.color, color: tag.color } : undefined}
                  onClick={() => setSelectedTagId(selectedTagId === tag.id ? null : tag.id)}
                >
                  {tag.name}
                  <span className="ml-1 opacity-60">{tag.artifact_count}</span>
                </Badge>
              ))}
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Clear filters */}
      {hasActiveFilter && (
        <>
          <Separator />
          <div className="p-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-xs gap-1.5 text-muted-foreground hover:text-foreground"
              onClick={clearFilters}
            >
              <X size={12} />
              Clear filters
            </Button>
          </div>
        </>
      )}
    </aside>
  )
}
