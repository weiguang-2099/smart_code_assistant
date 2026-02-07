/**
 * User profile and preference types
 */

// ==================== Theme Types ====================

export type Theme = 'light' | 'dark' | 'auto'

export type Language = 'zh-CN' | 'en-US'

// ==================== UserProfile Types ====================

export interface UserProfile {
  id: number
  user_id: number
  display_name: string | null
  bio: string | null
  avatar_url: string | null
  location: string | null
  website: string | null
  github_url: string | null
  updated_at: string
}

export interface UserProfileDetail extends UserProfile {
  username: string | null
  email: string | null
}

export interface UserProfileUpdate {
  display_name?: string
  bio?: string
  location?: string
  website?: string
  github_url?: string
}

// ==================== Avatar Upload Types ====================

export interface AvatarUploadResponse {
  avatar_url: string
}

// ==================== UserPreference Types ====================

export interface UserPreference {
  id: number
  user_id: number
  theme: Theme
  language: Language
  editor_font_size: number
  editor_theme: string
  notification_enabled: boolean
  email_notification: boolean
  created_at: string
  updated_at: string
}

export interface UserPreferenceUpdate {
  theme?: Theme
  language?: Language
  editor_font_size?: number
  editor_theme?: string
  notification_enabled?: boolean
  email_notification?: boolean
}

// ==================== User Stats Types ====================

export interface UserStats {
  documents_count: number
  total_versions: number
  projects_count: number
  storage_used: number
}

// ==================== Full User Profile Types ====================

export interface FullUserProfile {
  profile: UserProfile
  preferences: UserPreference
  stats: UserStats
}

// ==================== Auth Types (existing) ====================

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface AuthTokens {
  access_token: string
  token_type: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  full_name?: string
}
