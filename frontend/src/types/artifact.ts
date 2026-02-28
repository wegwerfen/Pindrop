export interface Tag {
  id: string
  name: string
  color: string | null
  source?: string
  artifact_count?: number
}

export interface Collection {
  id: string
  name: string
  description: string | null
  created_at: string
  artifact_count?: number
}

export interface Artifact {
  id: string
  plugin_type: string
  title: string
  excerpt: string | null
  thumbnail_path: string | null
  captured_at: string
  source_url: string | null
  source_domain: string | null
  is_archived: boolean
  is_read: boolean
  importance: number
  tags: Tag[]
}

export type GridItem =
  | { type: 'artifact'; data: Artifact }
  | { type: 'loading'; id: string }
