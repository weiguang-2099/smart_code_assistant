/**
 * Document types for Raw materials library
 */

// Source type enum for document versions
export type SourceType = 'upload' | 'manual' | 'parsed'

// ==================== Document Types ====================

export interface Document {
  id: number
  user_id: number
  document_number: string | null
  title: string
  description: string | null
  category: string | null
  project_id: number | null
  current_version_id: number | null
  is_published: boolean
  version_count: number
  created_at: string
  updated_at: string
}


// ==================== Outline Types ====================

export interface OutlineItem {
  level: number
  text: string
  anchor: string
  line_number: number | null
  children: OutlineItem[]
}

export interface DocumentOutlineResponse {
  document_id: number
  outline: OutlineItem[]
}

export interface DocumentCreate {
  title: string
  description?: string
  category?: string
  project_id?: number
}

export interface DocumentUpdate {
  title?: string
  description?: string
  category?: string
}

// ==================== Version Types ====================

export interface Version {
  id: number
  document_id: number
  version_number: number
  markdown_content: string
  tiptap_content: TipTapContent
  change_summary: string | null
  source_type: SourceType
  created_by: number
  created_at: string
}

export interface VersionCreate {
  markdown_content: string
  tiptap_content?: TipTapContent
  source_type?: SourceType
  change_summary?: string
}

export interface VersionListItem {
  id: number
  document_id: number
  version_number: number
  change_summary: string | null
  source_type: SourceType
  created_by: number
  created_by_username: string | null
  created_at: string
}

// ==================== Document Detail Types ====================

export interface DocumentDetail extends Document {
  current_version: Version | null
  versions: VersionListItem[]
}

// ==================== List Response Types ====================

export interface DocumentListResponse {
  items: Document[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DocumentListParams {
  page?: number
  page_size?: number
  category?: string
  project_id?: number
  search?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

// ==================== Version Compare Types ====================

export interface VersionCompareResponse {
  from_version: Version
  to_version: Version
  diff: string
}

export interface VersionRollbackRequest {
  version_id: number
  change_summary?: string
}

export interface VersionRollbackResponse {
  new_version_id: number
  version_number: number
  message: string
}

// ==================== PDF Upload Types ====================

export interface PDFUploadResponse {
  document_id: number
  version_id: number
  markdown_content: string
  tiptap_content: TipTapContent
}

// ==================== TipTap Types ====================

export interface TipTapContent {
  type: string
  content?: TipTapNode[]
  attrs?: Record<string, unknown>
}

export interface TipTapNode {
  type: string
  content?: TipTapNode[]
  attrs?: Record<string, unknown>
  marks?: TipTapMark[]
  text?: string
}

export interface TipTapMark {
  type: string
  attrs?: Record<string, unknown>
}

// ==================== Attachment Types ====================

export interface Attachment {
  id: number
  version_id: number
  file_name: string
  file_type: string
  file_size: number
  storage_path: string
  storage_type: string
  created_at: string
}

// ==================== Stats Types ====================

export interface DocumentStatsResponse {
  documents_count: number
  total_versions: number
  projects_count: number
  storage_used: number
}
