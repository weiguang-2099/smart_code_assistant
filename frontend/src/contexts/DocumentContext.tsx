import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { documentService } from '../services/documentService'
import type {
  Document,
  DocumentDetail,
  Version,
  VersionListItem,
  VersionCompareResponse,
  TipTapContent,
} from '../types/document'

interface DocumentContextValue {
  // Current document state
  document: DocumentDetail | null
  loading: boolean
  error: string | null

  // Current editing state
  currentContent: TipTapContent | null
  hasUnsavedChanges: boolean

  // Version state
  versions: VersionListItem[]
  viewingVersionId: number | null
  comparingVersions: number[] | null
  comparisonResult: VersionCompareResponse | null

  // Actions
  loadDocument: (documentId: number) => Promise<void>
  saveContent: (markdown: string, tiptap: TipTapContent, summary?: string) => Promise<void>
  createVersion: (markdown: string, tiptap: TipTapContent, summary?: string) => Promise<void>
  rollbackVersion: (versionId: number, summary?: string) => Promise<void>
  viewVersion: (versionId: number) => Promise<void>
  compareVersions: (fromId: number, toId: number) => Promise<void>
  closeComparison: () => void
  clearDocument: () => void
  setCurrentContent: (content: TipTapContent) => void

  // Update metadata
  updateMetadata: (data: { title?: string; description?: string; category?: string }) => Promise<void>
}

const DocumentContext = createContext<DocumentContextValue | undefined>(undefined)

export function useDocument() {
  const context = useContext(DocumentContext)
  if (!context) {
    throw new Error('useDocument must be used within DocumentProvider')
  }
  return context
}

interface DocumentProviderProps {
  token: string
  children: ReactNode
}

export function DocumentProvider({ token, children }: DocumentProviderProps) {
  const [document, setDocument] = useState<DocumentDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [currentContent, setCurrentContent] = useState<TipTapContent | null>(null)
  const [originalContent, setOriginalContent] = useState<TipTapContent | null>(null)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  const [versions, setVersions] = useState<VersionListItem[]>([])
  const [viewingVersionId, setViewingVersionId] = useState<number | null>(null)
  const [comparingVersions, setComparingVersions] = useState<number[] | null>(null)
  const [comparisonResult, setComparisonResult] = useState<VersionCompareResponse | null>(null)

  /**
   * Load a document with all its versions
   */
  const loadDocument = useCallback(async (documentId: number) => {
    setLoading(true)
    setError(null)

    try {
      const doc = await documentService.getDocument(token, documentId)
      setDocument(doc)
      setVersions(doc.versions || [])

      // Set current content from the latest version
      if (doc.current_version) {
        setCurrentContent(doc.current_version.tiptap_content)
        setOriginalContent(doc.current_version.tiptap_content)
        setHasUnsavedChanges(false)
      } else {
        setCurrentContent({ type: 'doc', content: [] })
        setOriginalContent({ type: 'doc', content: [] })
      }

      setViewingVersionId(null)
      setComparingVersions(null)
      setComparisonResult(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document')
      setDocument(null)
    } finally {
      setLoading(false)
    }
  }, [token])

  /**
   * Save content as a new version
   */
  const saveContent = useCallback(async (
    markdown: string,
    tiptap: TipTapContent,
    summary?: string
  ) => {
    if (!document) return

    setLoading(true)
    setError(null)

    try {
      const newVersion = await documentService.updateDocumentContent(token, document.id, {
        markdown_content: markdown,
        tiptap_content: tiptap,
        change_summary: summary,
      })

      // Update local state
      setCurrentContent(newVersion.tiptap_content)
      setOriginalContent(newVersion.tiptap_content)
      setHasUnsavedChanges(false)

      // Reload document to get updated versions list
      await loadDocument(document.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save content')
      throw err
    } finally {
      setLoading(false)
    }
  }, [document, token, loadDocument])

  /**
   * Create a new version (alias for saveContent)
   */
  const createVersion = useCallback(async (
    markdown: string,
    tiptap: TipTapContent,
    summary?: string
  ) => {
    return saveContent(markdown, tiptap, summary)
  }, [saveContent])

  /**
   * Rollback to a specific version
   */
  const rollbackVersion = useCallback(async (versionId: number, summary?: string) => {
    if (!document) return

    setLoading(true)
    setError(null)

    try {
      const result = await documentService.rollbackVersion(token, document.id, {
        version_id: versionId,
        change_summary: summary,
      })

      // Reload document
      await loadDocument(document.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollback version')
      throw err
    } finally {
      setLoading(false)
    }
  }, [document, token, loadDocument])

  /**
   * View a specific version
   */
  const viewVersion = useCallback(async (versionId: number) => {
    if (!document) return

    setLoading(true)
    setError(null)

    try {
      const version = await documentService.getVersion(token, document.id, versionId)
      setCurrentContent(version.tiptap_content)
      setViewingVersionId(versionId)
      setHasUnsavedChanges(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load version')
    } finally {
      setLoading(false)
    }
  }, [document, token])

  /**
   * Compare two versions
   */
  const compareVersions = useCallback(async (fromId: number, toId: number) => {
    if (!document) return

    setLoading(true)
    setError(null)

    try {
      const comparison = await documentService.compareVersions(token, document.id, fromId, toId)
      setComparisonResult(comparison)
      setComparingVersions([fromId, toId])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare versions')
    } finally {
      setLoading(false)
    }
  }, [document, token])

  /**
   * Close version comparison
   */
  const closeComparison = useCallback(() => {
    setComparingVersions(null)
    setComparisonResult(null)
  }, [])

  /**
   * Clear the current document
   */
  const clearDocument = useCallback(() => {
    setDocument(null)
    setCurrentContent(null)
    setOriginalContent(null)
    setHasUnsavedChanges(false)
    setVersions([])
    setViewingVersionId(null)
    setComparingVersions(null)
    setComparisonResult(null)
    setError(null)
  }, [])

  /**
   * Update document metadata
   */
  const updateMetadata = useCallback(async (data: {
    title?: string
    description?: string
    category?: string
  }) => {
    if (!document) return

    setLoading(true)
    setError(null)

    try {
      const updated = await documentService.updateDocumentMetadata(token, document.id, data)
      setDocument((prev) => prev ? { ...prev, ...updated } : null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update metadata')
      throw err
    } finally {
      setLoading(false)
    }
  }, [document, token])

  // Check for unsaved changes when content changes
  const updateCurrentContent = useCallback((content: TipTapContent) => {
    setCurrentContent(content)
    setHasUnsavedChanges(JSON.stringify(content) !== JSON.stringify(originalContent))
  }, [originalContent])

  const value: DocumentContextValue = {
    document,
    loading,
    error,
    currentContent,
    hasUnsavedChanges,
    versions,
    viewingVersionId,
    comparingVersions,
    loadDocument,
    saveContent,
    createVersion,
    rollbackVersion,
    viewVersion,
    compareVersions,
    closeComparison,
    clearDocument,
    updateMetadata,
    // Add internal methods for content updates
    setCurrentContent: updateCurrentContent,
    comparisonResult,
  }

  return (
    <DocumentContext.Provider value={value}>
      {children}
    </DocumentContext.Provider>
  )
}
