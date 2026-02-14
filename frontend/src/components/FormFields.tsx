import React, { forwardRef, InputHTMLAttributes, TextareaHTMLAttributes, SelectHTMLAttributes } from 'react'

interface BaseFieldProps {
  label?: string
  error?: string
  helperText?: string
  required?: boolean
  className?: string
}

interface InputFieldProps extends BaseFieldProps, InputHTMLAttributes<HTMLInputElement> {
  type?: 'text' | 'email' | 'password' | 'number' | 'url' | 'tel'
}

interface TextareaFieldProps extends BaseFieldProps, TextareaHTMLAttributes<HTMLTextAreaElement> {}

interface SelectFieldProps extends BaseFieldProps, SelectHTMLAttributes<HTMLSelectElement> {
  options: { value: string; label: string }[]
}

/**
 * Input field component with label, error display, and helper text
 */
export const InputField = forwardRef<HTMLInputElement, InputFieldProps>(
  ({ label, error, helperText, required, className = '', ...props }, ref) => {
    const inputId = props.id || props.name

    return (
      <div className={`space-y-1.5 ${className}`}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-cyan-300"
          >
            {label}
            {required && <span className="text-red-400 ml-1">*</span>}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`
            w-full px-4 py-2.5
            bg-gray-900/50
            border rounded
            text-gray-100 placeholder-gray-500
            transition-all duration-150
            focus:outline-none focus:ring-2
            ${error
              ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20'
              : 'border-cyan-500/30 focus:border-cyan-500 focus:ring-cyan-500/20'
            }
          `}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
          {...props}
        />
        {error && (
          <p id={`${inputId}-error`} className="text-sm text-red-400 flex items-center gap-1" role="alert">
            <span aria-hidden="true">⚠</span>
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={`${inputId}-helper`} className="text-xs text-gray-500">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

InputField.displayName = 'InputField'

/**
 * Textarea field component
 */
export const TextareaField = forwardRef<HTMLTextAreaElement, TextareaFieldProps>(
  ({ label, error, helperText, required, className = '', ...props }, ref) => {
    const inputId = props.id || props.name

    return (
      <div className={`space-y-1.5 ${className}`}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-cyan-300"
          >
            {label}
            {required && <span className="text-red-400 ml-1">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          className={`
            w-full px-4 py-2.5
            bg-gray-900/50
            border rounded
            text-gray-100 placeholder-gray-500
            transition-all duration-150
            focus:outline-none focus:ring-2
            resize-y min-h-[100px]
            ${error
              ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20'
              : 'border-cyan-500/30 focus:border-cyan-500 focus:ring-cyan-500/20'
            }
          `}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
          {...props}
        />
        {error && (
          <p id={`${inputId}-error`} className="text-sm text-red-400 flex items-center gap-1" role="alert">
            <span aria-hidden="true">⚠</span>
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={`${inputId}-helper`} className="text-xs text-gray-500">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

TextareaField.displayName = 'TextareaField'

/**
 * Select field component
 */
export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(
  ({ label, error, helperText, required, options, className = '', ...props }, ref) => {
    const inputId = props.id || props.name

    return (
      <div className={`space-y-1.5 ${className}`}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-cyan-300"
          >
            {label}
            {required && <span className="text-red-400 ml-1">*</span>}
          </label>
        )}
        <select
          ref={ref}
          id={inputId}
          className={`
            w-full px-4 py-2.5
            bg-gray-900/50
            border rounded
            text-gray-100
            transition-all duration-150
            focus:outline-none focus:ring-2
            cursor-pointer
            ${error
              ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20'
              : 'border-cyan-500/30 focus:border-cyan-500 focus:ring-cyan-500/20'
            }
          `}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p id={`${inputId}-error`} className="text-sm text-red-400 flex items-center gap-1" role="alert">
            <span aria-hidden="true">⚠</span>
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={`${inputId}-helper`} className="text-xs text-gray-500">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

SelectField.displayName = 'SelectField'

/**
 * Password field with show/hide toggle
 */
export const PasswordField = forwardRef<HTMLInputElement, InputFieldProps>(
  ({ className = '', ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false)

    return (
      <div className="relative">
        <InputField
          ref={ref}
          type={showPassword ? 'text' : 'password'}
          className={className}
          {...props}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute right-3 top-[38px] text-gray-400 hover:text-cyan-300 transition-colors"
          tabIndex={-1}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          )}
        </button>
      </div>
    )
  }
)

PasswordField.displayName = 'PasswordField'

/**
 * Password strength indicator
 */
export const PasswordStrength: React.FC<{ password: string }> = ({ password }) => {
  const { score, label, color } = React.useMemo(() => {
    let s = 0
    if (password.length >= 6) s++
    if (password.length >= 10) s++
    if (/[a-z]/.test(password)) s++
    if (/[A-Z]/.test(password)) s++
    if (/\d/.test(password)) s++
    if (/[@$!%*?&]/.test(password)) s++

    if (s <= 2) return { score: s, label: 'Weak', color: 'bg-red-500', textColor: 'text-red-400' }
    if (s <= 4) return { score: s, label: 'Medium', color: 'bg-yellow-500', textColor: 'text-yellow-400' }
    return { score: s, label: 'Strong', color: 'bg-green-500', textColor: 'text-green-400' }
  }, [password])

  if (!password) return null

  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1 bg-gray-700 rounded overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${color}`}
          style={{ width: `${(score / 6) * 100}%` }}
        />
      </div>
      <span className={`text-xs ${color.replace('bg-', 'text-')}`}>{label}</span>
    </div>
  )
}

/**
 * Checkbox field component
 */
interface CheckboxFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string
  error?: string
}

export const CheckboxField = forwardRef<HTMLInputElement, CheckboxFieldProps>(
  ({ label, error, className = '', ...props }, ref) => {
    const inputId = props.id || props.name

    return (
      <div className={`flex items-start gap-2 ${className}`}>
        <input
          ref={ref}
          type="checkbox"
          id={inputId}
          className="
            mt-1 w-4 h-4
            bg-gray-900/50
            border border-cyan-500/30 rounded
            text-cyan-500
            focus:ring-2 focus:ring-cyan-500/20 focus:ring-offset-0
            cursor-pointer
          "
          aria-invalid={error ? 'true' : 'false'}
          {...props}
        />
        <div className="flex flex-col">
          <label htmlFor={inputId} className="text-sm text-gray-300 cursor-pointer">
            {label}
          </label>
          {error && (
            <p className="text-sm text-red-400" role="alert">
              {error}
            </p>
          )}
        </div>
      </div>
    )
  }
)

CheckboxField.displayName = 'CheckboxField'
