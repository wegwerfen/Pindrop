import { useState, useCallback } from 'react'
import { AnimatePresence } from 'framer-motion'
import { useDropZone } from '@/hooks/useDropZone'
import { useIngest } from '@/hooks/useIngest'
import ArtifactGrid from '@/components/grid/ArtifactGrid'
import DropZoneOverlay from '@/components/dropzone/DropZoneOverlay'
import type { GridItem } from '@/types/artifact'

export default function MainArea() {
  const { isDragOver } = useDropZone()
  const ingest = useIngest()
  const [pendingItems, setPendingItems] = useState<GridItem[]>([])

  const handleDrop = useCallback(
    async (url: string) => {
      const loadingId = crypto.randomUUID()
      setPendingItems((prev) => [{ type: 'loading', id: loadingId }, ...prev])
      try {
        await ingest.mutateAsync(url)
      } finally {
        setPendingItems((prev) => prev.filter((item) => item.id !== loadingId))
      }
    },
    [ingest],
  )

  return (
    <main className="flex-1 overflow-y-auto relative">
      <ArtifactGrid pendingItems={pendingItems} />
      <AnimatePresence>
        {isDragOver && <DropZoneOverlay onDrop={handleDrop} />}
      </AnimatePresence>
    </main>
  )
}
