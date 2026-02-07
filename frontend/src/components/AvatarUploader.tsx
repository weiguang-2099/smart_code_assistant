import { useState, useRef } from 'react'

interface AvatarUploaderProps {
  currentAvatar: string | null
  onUpload: (file: File) => Promise<void>
  size?: 'sm' | 'md' | 'lg'
}

export default function AvatarUploader({
  currentAvatar,
  onUpload,
  size = 'lg'
}: AvatarUploaderProps) {
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const sizeClasses = {
    sm: 'w-16 h-16',
    md: 'w-24 h-24',
    lg: 'w-32 h-32',
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file')
      return
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('File size must be less than 5MB')
      return
    }

    // Create preview
    const reader = new FileReader()
    reader.onloadend = () => {
      setPreview(reader.result as string)
    }
    reader.readAsDataURL(file)

    // Upload
    setUploading(true)
    try {
      await onUpload(file)
    } finally {
      setUploading(false)
    }
  }

  const getAvatarSrc = () => {
    if (preview) return preview
    if (currentAvatar) return currentAvatar
    // Default avatar
    return 'data:image/svg+xml,' + encodeURIComponent(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%236b7280">
        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
      </svg>
    `)
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative group">
        {/* Avatar */}
        <div
          className={`
            ${sizeClasses[size]} rounded-full overflow-hidden
            border-2 border-purple-500/50
            bg-gray-800 flex items-center justify-center
            transition-all group-hover:border-purple-400
          `}
        >
          {uploading ? (
            <div className="animate-spin text-2xl text-purple-400">⟳</div>
          ) : (
            <img
              src={getAvatarSrc()}
              alt="Avatar"
              className="w-full h-full object-cover"
            />
          )}
        </div>

        {/* Upload Overlay */}
        <button
          onClick={() => !uploading && fileInputRef.current?.click()}
          disabled={uploading}
          className={`
            absolute inset-0 flex items-center justify-center
            bg-black/60 rounded-full opacity-0 group-hover:opacity-100
            transition-opacity
            ${uploading ? 'cursor-wait' : 'cursor-pointer'}
          `}
        >
          <span className="text-2xl">{uploading ? '⏳' : '📷'}</span>
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
          disabled={uploading}
        />
      </div>

      <div className="text-center text-sm text-gray-400">
        {uploading ? (
          <span>Uploading...</span>
        ) : (
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-purple-400 hover:text-purple-300 underline"
          >
            Change Avatar
          </button>
        )}
      </div>

      {preview && !uploading && (
        <button
          onClick={() => setPreview(null)}
          className="text-xs text-red-400 hover:text-red-300"
        >
          Discard changes
        </button>
      )}
    </div>
  )
}
