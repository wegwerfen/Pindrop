import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { Upload } from 'lucide-react'

interface DropZoneOverlayProps {
  onDrop: (url: string) => void
}

function extractUrl(e: DragEvent): string | null {
  const transfer = e.dataTransfer
  if (!transfer) return null

  // Primary: text/uri-list (browsers set this on link drags)
  const uriList = transfer.getData('text/uri-list')
  if (uriList) {
    const first = uriList.split('\n').find((u) => u.trim() && !u.startsWith('#'))
    if (first) return first.trim()
  }

  // Fallback: plain text URL
  const plain = transfer.getData('text/plain')
  if (plain?.startsWith('http')) return plain.trim()

  return null
}

export default function DropZoneOverlay({ onDrop }: DropZoneOverlayProps) {
  useEffect(() => {
    const handleDrop = (e: DragEvent) => {
      e.preventDefault()
      const url = extractUrl(e)
      if (url) onDrop(url)
    }

    window.addEventListener('drop', handleDrop)
    return () => window.removeEventListener('drop', handleDrop)
  }, [onDrop])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background/80 backdrop-blur-sm pointer-events-none"
    >
      <div className="flex flex-col items-center gap-3 rounded-xl border-2 border-dashed border-primary/50 bg-background/90 px-16 py-12 shadow-2xl">
        <Upload size={40} className="text-primary/60" />
        <p className="text-base font-medium text-foreground">Drop to save</p>
        <p className="text-xs text-muted-foreground">Release any URL to add it to Pindrop</p>
      </div>
    </motion.div>
  )
}
