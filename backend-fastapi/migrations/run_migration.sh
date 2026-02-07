#!/bin/bash
mysql -u appuser -papppassword smart_code_assistant << 'EOF'
-- Migration: Add documents, raw_versions, attachments, user_profile, user_preferences tables
-- Date: 2026-02-07
-- Description: Add tables for Raw materials library with version control and user preferences

-- ============================================
-- 1. Create documents table
-- ============================================
CREATE TABLE IF NOT EXISTS documents (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    category VARCHAR(100) NULL,
    project_id INT NULL,
    current_version_id BIGINT NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_project_id (project_id),
    INDEX idx_category (category),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 2. Create raw_versions table
-- ============================================
CREATE TABLE IF NOT EXISTS raw_versions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    document_id BIGINT NOT NULL,
    version_number INT NOT NULL,
    markdown_content LONGTEXT NOT NULL,
    tiptap_content JSON NOT NULL,
    source_type VARCHAR(20) NOT NULL DEFAULT 'manual',
    change_summary VARCHAR(500) NULL,
    created_by INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_document_id (document_id),
    INDEX idx_created_at (created_at),
    UNIQUE KEY uk_document_version (document_id, version_number),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. Create attachments table
-- ============================================
CREATE TABLE IF NOT EXISTS attachments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    version_id BIGINT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    storage_type VARCHAR(20) NOT NULL DEFAULT 'local',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_version_id (version_id),
    FOREIGN KEY (version_id) REFERENCES raw_versions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 4. Create user_profile table
-- ============================================
CREATE TABLE IF NOT EXISTS user_profile (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    display_name VARCHAR(100) NULL,
    bio TEXT NULL,
    avatar_url VARCHAR(500) NULL,
    location VARCHAR(100) NULL,
    website VARCHAR(255) NULL,
    github_url VARCHAR(255) NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 5. Create user_preferences table
-- ============================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    theme VARCHAR(20) NOT NULL DEFAULT 'dark',
    language VARCHAR(10) NOT NULL DEFAULT 'zh-CN',
    editor_font_size INT NOT NULL DEFAULT 14,
    editor_theme VARCHAR(50) NOT NULL DEFAULT 'monokai',
    notification_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    email_notification BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 6. Add foreign key to documents.current_version_id (deferred)
-- ============================================
-- This will be added after raw_versions table is confirmed to exist
-- ALTER TABLE documents ADD CONSTRAINT fk_documents_current_version
--     FOREIGN KEY (current_version_id) REFERENCES raw_versions(id) ON DELETE SET NULL;

EOF
