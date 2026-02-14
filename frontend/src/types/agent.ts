/**
 * Agent (Digital Human) types for AI assistant management
 */

// ==================== Agent Status Types ====================

export type AgentStatus = 'draft' | 'active' | 'inactive' | 'training'
export type TrainingStatus = 'pending' | 'running' | 'completed' | 'failed'

// ==================== Agent Types ====================

export interface Agent {
  id: number
  user_id: number
  name: string
  description: string | null
  domain: string | null
  avatar_url: string | null
  status: AgentStatus
  conversation_count: number
  created_at: string
  updated_at: string
}

export interface AgentDetail extends Agent {
  system_prompt: string | null
  config: Record<string, unknown> | null
}

export interface AgentCreate {
  name: string
  domain?: string
  description?: string
  system_prompt?: string
  config?: Record<string, unknown>
}

export interface AgentUpdate {
  name?: string
  domain?: string
  description?: string
  avatar_url?: string
  system_prompt?: string
  config?: Record<string, unknown>
}

export interface AgentStatusUpdate {
  status: AgentStatus
}

export interface AgentListResponse {
  items: Agent[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ==================== Message Types ====================

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  tokens: number | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface MessageCreate {
  role: string
  content: string
}

// ==================== Conversation Types ====================

export interface Conversation {
  id: number
  agent_id: number
  user_id: number
  title: string | null
  summary: string | null
  message_count: number
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface ConversationCreate {
  agent_id: number
  title?: string
  summary?: string
}

export interface ConversationUpdate {
  title?: string
  summary?: string
}

export interface ConversationListResponse {
  items: Conversation[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ==================== Training Task Types ====================

export interface TrainingTask {
  id: number
  agent_id: number
  user_id: number
  name: string
  description: string | null
  status: TrainingStatus
  progress: number
  result: Record<string, unknown> | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface TrainingTaskCreate {
  agent_id: number
  name: string
  description?: string
  training_data?: Record<string, unknown>
  config?: Record<string, unknown>
}

export interface TrainingTaskListResponse {
  items: TrainingTask[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ==================== Chat Types ====================

export interface ChatRequest {
  message: string
  conversation_id?: number
}

export interface ChatResponse {
  conversation_id: number
  message: Message
}

// ==================== Agent Name Suggestion Types ====================

export interface AgentNameSuggestionRequest {
  domain: string
  description?: string
}

export interface AgentNameSuggestionResponse {
  names: string[]
  domain: string
}
