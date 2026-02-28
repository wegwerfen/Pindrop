// Phase 1: hardcoded map. Phase 2: load dynamically from /api/plugins + frontend.json.
import { Globe, Image, FileText, File } from 'lucide-react'
import type { ComponentType } from 'react'

interface PluginMeta {
  Icon: ComponentType<{ size?: number; className?: string }>
  accent: string
  label: string
}

const PLUGIN_REGISTRY: Record<string, PluginMeta> = {
  webpage: { Icon: Globe,     accent: '#4A90D9', label: 'Webpage' },
  image:   { Icon: Image,     accent: '#E67E22', label: 'Image'   },
  note:    { Icon: FileText,  accent: '#27AE60', label: 'Note'    },
  pdf:     { Icon: File,      accent: '#E74C3C', label: 'PDF'     },
}

export function getPluginMeta(pluginType: string): PluginMeta {
  return PLUGIN_REGISTRY[pluginType] ?? {
    Icon: File,
    accent: '#888888',
    label: pluginType,
  }
}
