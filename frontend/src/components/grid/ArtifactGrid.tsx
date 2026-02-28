import Masonry from 'react-masonry-css'
import { useArtifacts } from '@/hooks/useArtifacts'
import ArtifactCard from './ArtifactCard'
import LoadingCard from './LoadingCard'
import type { GridItem } from '@/types/artifact'

const BREAKPOINTS = {
  default: 4,
  1280: 3,
  900: 2,
  600: 1,
}

interface ArtifactGridProps {
  pendingItems: GridItem[]
}

export default function ArtifactGrid({ pendingItems }: ArtifactGridProps) {
  const { data: artifacts = [], isLoading, isError } = useArtifacts()

  if (isError) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        Failed to load — is the backend running on port 8002?
      </div>
    )
  }

  const allItems: GridItem[] = [
    ...pendingItems,
    ...artifacts.map((a) => ({ type: 'artifact' as const, data: a })),
  ]

  if (isLoading && allItems.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        Loading...
      </div>
    )
  }

  if (allItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2 text-muted-foreground">
        <p className="text-sm font-medium">Nothing here yet.</p>
        <p className="text-xs">Drag a URL onto the window to save it.</p>
      </div>
    )
  }

  return (
    <div className="p-4">
      <Masonry
        breakpointCols={BREAKPOINTS}
        className="flex -ml-4 w-auto"
        columnClassName="pl-4 bg-clip-padding"
      >
        {allItems.map((item) =>
          item.type === 'loading' ? (
            <LoadingCard key={item.id} />
          ) : (
            <ArtifactCard key={item.data.id} artifact={item.data} />
          ),
        )}
      </Masonry>
    </div>
  )
}
