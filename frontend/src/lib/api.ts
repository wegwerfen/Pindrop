import type { Artifact, Tag, Collection } from '@/types/artifact'

export type SortOption =
  | 'captured_at_desc'
  | 'captured_at_asc'
  | 'title_asc'
  | 'importance_desc'

export interface ArtifactFilters {
  sort?: SortOption
  tag_id?: string
  collection_id?: string
  is_archived?: boolean
  limit?: number
  offset?: number
}

export async function fetchArtifacts(filters: ArtifactFilters = {}): Promise<Artifact[]> {
  const params = new URLSearchParams()
  if (filters.sort)          params.set('sort', filters.sort)
  if (filters.tag_id)        params.set('tag_id', filters.tag_id)
  if (filters.collection_id) params.set('collection_id', filters.collection_id)
  params.set('is_archived', String(filters.is_archived ?? false))
  params.set('limit', String(filters.limit ?? 50))
  params.set('offset', String(filters.offset ?? 0))

  const res = await fetch(`/api/artifacts?${params}`)
  if (!res.ok) throw new Error(`Failed to fetch artifacts: ${res.statusText}`)
  return res.json()
}

export async function fetchTags(): Promise<Tag[]> {
  const res = await fetch('/api/tags')
  if (!res.ok) throw new Error('Failed to fetch tags')
  return res.json()
}

export async function fetchCollections(): Promise<Collection[]> {
  const res = await fetch('/api/collections')
  if (!res.ok) throw new Error('Failed to fetch collections')
  return res.json()
}

export async function searchArtifacts(q: string): Promise<Artifact[]> {
  const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`)
  if (!res.ok) throw new Error('Search failed')
  return res.json()
}

export async function ingestUrl(url: string): Promise<Artifact> {
  const res = await fetch(`/api/ingest?url=${encodeURIComponent(url)}`, {
    method: 'POST',
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `Ingest failed: ${res.statusText}`)
  }
  return res.json()
}
