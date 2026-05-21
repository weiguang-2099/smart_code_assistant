import { useState, useCallback, useMemo } from 'react'

export type ValidationRule<T> = {
  required?: boolean | string
  minLength?: number | { value: number; message: string }
  maxLength?: number | { value: number; message: string }
  pattern?: RegExp | { value: RegExp; message: string }
  validate?: (value: T) => string | boolean | undefined
  custom?: (value: T, formData: Record<string, unknown>) => string | undefined
}

export type ValidationRules<T extends Record<string, unknown>> = {
  [K in keyof T]?: ValidationRule<T[K]>
}

export type FormErrors<T extends Record<string, unknown>> = {
  [K in keyof T]?: string
}

export type FormTouched<T extends Record<string, unknown>> = {
  [K in keyof T]?: boolean
}

interface UseFormOptions<T extends Record<string, unknown>> {
  initialValues: T
  validationRules?: ValidationRules<T>
  onSubmit: (values: T) => Promise<void> | void
  validateOnChange?: boolean
  validateOnBlur?: boolean
}

interface UseFormReturn<T extends Record<string, unknown>> {
  values: T
  errors: FormErrors<T>
  touched: FormTouched<T>
  isSubmitting: boolean
  isValid: boolean
  isDirty: boolean
  handleChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
  handleBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
  setValue: <K extends keyof T>(field: K, value: T[K]) => void
  setFieldError: <K extends keyof T>(field: K, error: string) => void
  setTouched: <K extends keyof T>(field: K, isTouched?: boolean) => void
  validateField: <K extends keyof T>(field: K) => string | undefined
  validateForm: () => boolean
  resetForm: () => void
  resetField: <K extends keyof T>(field: K) => void
  handleSubmit: (e: React.FormEvent) => Promise<void>
  getFieldProps: <K extends keyof T>(field: K) => {
    name: K
    // Always serialised to string for the underlying <input>; getFieldProps
    // is intended for binding into HTMLInputElement.value etc.
    value: string
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
    onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
  }
  getFieldError: <K extends keyof T>(field: K) => string | undefined
  hasError: <K extends keyof T>(field: K) => boolean
}

const defaultMessages = {
  required: 'This field is required',
  minLength: (min: number) => `Must be at least ${min} characters`,
  maxLength: (max: number) => `Must be no more than ${max} characters`,
  pattern: 'Invalid format',
}

export function useForm<T extends Record<string, unknown>>({
  initialValues,
  validationRules = {},
  onSubmit,
  validateOnChange = true,
  validateOnBlur = true,
}: UseFormOptions<T>): UseFormReturn<T> {
  const [values, setValues] = useState<T>(initialValues)
  const [errors, setErrors] = useState<FormErrors<T>>({})
  const [touched, setTouchedState] = useState<FormTouched<T>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDirty, setIsDirty] = useState(false)

  const validateField = useCallback(
    <K extends keyof T>(field: K): string | undefined => {
      const rules = validationRules[field]
      if (!rules) return undefined

      const value = values[field]

      // Required
      if (rules.required) {
        const isEmpty = value === undefined || value === null || value === ''
        if (isEmpty) {
          return typeof rules.required === 'string' ? rules.required : defaultMessages.required
        }
      }

      // String validations
      if (typeof value === 'string') {
        // Min length
        if (rules.minLength !== undefined) {
          const minLengthConfig = typeof rules.minLength === 'number'
            ? { value: rules.minLength, message: defaultMessages.minLength(rules.minLength) }
            : { value: rules.minLength.value, message: rules.minLength.message }
          if (value.length < minLengthConfig.value) {
            return minLengthConfig.message
          }
        }

        // Max length
        if (rules.maxLength !== undefined) {
          const maxLengthConfig = typeof rules.maxLength === 'number'
            ? { value: rules.maxLength, message: defaultMessages.maxLength(rules.maxLength) }
            : { value: rules.maxLength.value, message: rules.maxLength.message }
          if (value.length > maxLengthConfig.value) {
            return maxLengthConfig.message
          }
        }

        // Pattern
        if (rules.pattern) {
          const patternConfig = rules.pattern instanceof RegExp
            ? { value: rules.pattern, message: defaultMessages.pattern }
            : { value: rules.pattern.value, message: rules.pattern.message }
          if (!patternConfig.value.test(value)) {
            return patternConfig.message
          }
        }
      }

      // Custom validation function
      if (rules.validate) {
        const result = rules.validate(value)
        if (typeof result === 'string') return result
        if (result === false) return 'Invalid value'
      }

      // Custom validation with form data access
      if (rules.custom) {
        const result = rules.custom(value, values)
        if (result) return result
      }

      return undefined
    },
    [values, validationRules]
  )

  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors<T> = {}
    let isValid = true

    for (const field in validationRules) {
      const error = validateField(field as keyof T)
      if (error) {
        newErrors[field as keyof T] = error
        isValid = false
      }
    }

    setErrors(newErrors)
    return isValid
  }, [validateField, validationRules])

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const { name, value, type } = e.target
      const fieldValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value

      setValues((prev) => ({ ...prev, [name]: fieldValue }))
      setIsDirty(true)

      // Validate on change if enabled
      if (validateOnChange && touched[name as keyof T]) {
        const error = validateField(name as keyof T)
        setErrors((prev) => ({
          ...prev,
          [name]: error,
        }))
      }
    },
    [validateOnChange, touched, validateField]
  )

  const handleBlur = useCallback(
    (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const { name } = e.target
      setTouchedState((prev) => ({ ...prev, [name]: true }))

      // Validate on blur if enabled
      if (validateOnBlur) {
        const error = validateField(name as keyof T)
        setErrors((prev) => ({
          ...prev,
          [name]: error,
        }))
      }
    },
    [validateOnBlur, validateField]
  )

  const setValue = useCallback(
    <K extends keyof T>(field: K, value: T[K]) => {
      setValues((prev) => ({ ...prev, [field]: value }))
      setIsDirty(true)
    },
    []
  )

  const setFieldError = useCallback(<K extends keyof T>(field: K, error: string) => {
    setErrors((prev) => ({ ...prev, [field]: error }))
  }, [])

  const setTouched = useCallback(<K extends keyof T>(field: K, isTouched = true) => {
    setTouchedState((prev) => ({ ...prev, [field]: isTouched }))
  }, [])

  const resetForm = useCallback(() => {
    setValues(initialValues)
    setErrors({})
    setTouchedState({})
    setIsSubmitting(false)
    setIsDirty(false)
  }, [initialValues])

  const resetField = useCallback(
    <K extends keyof T>(field: K) => {
      setValues((prev) => ({ ...prev, [field]: initialValues[field] }))
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[field]
        return newErrors
      })
      setTouchedState((prev) => ({ ...prev, [field]: false }))
    },
    [initialValues]
  )

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()

      // Mark all fields as touched
      const allTouched = Object.keys(validationRules).reduce(
        (acc, key) => ({ ...acc, [key]: true }),
        {} as FormTouched<T>
      )
      setTouchedState(allTouched)

      // Validate all fields
      const isValid = validateForm()

      if (!isValid) return

      setIsSubmitting(true)
      try {
        await onSubmit(values)
      } finally {
        setIsSubmitting(false)
      }
    },
    [values, validateForm, onSubmit, validationRules]
  )

  const getFieldProps = useCallback(
    <K extends keyof T>(field: K) => ({
      name: field,
      value: String(values[field] ?? ''),
      onChange: handleChange,
      onBlur: handleBlur,
    }),
    [values, handleChange, handleBlur]
  )

  const getFieldError = useCallback(
    <K extends keyof T>(field: K) => (touched[field] ? errors[field] : undefined),
    [errors, touched]
  )

  const hasError = useCallback(
    <K extends keyof T>(field: K) => Boolean(touched[field] && errors[field]),
    [errors, touched]
  )

  const isValid = useMemo(() => Object.keys(errors).length === 0, [errors])

  return {
    values,
    errors,
    touched,
    isSubmitting,
    isValid,
    isDirty,
    handleChange,
    handleBlur,
    setValue,
    setFieldError,
    setTouched,
    validateField,
    validateForm,
    resetForm,
    resetField,
    handleSubmit,
    getFieldProps,
    getFieldError,
    hasError,
  }
}

// Common validation patterns
export const patterns = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  url: /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([/\w .-]*)*\/?$/,
  username: /^[a-zA-Z0-9_]{3,50}$/,
  password: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{6,}$/,
  phone: /^\+?[\d\s-]{10,}$/,
}

// Password strength checker
export function getPasswordStrength(password: string): {
  score: number
  label: string
  color: string
} {
  let score = 0

  if (password.length >= 6) score++
  if (password.length >= 10) score++
  if (/[a-z]/.test(password)) score++
  if (/[A-Z]/.test(password)) score++
  if (/\d/.test(password)) score++
  if (/[@$!%*?&]/.test(password)) score++

  if (score <= 2) {
    return { score, label: 'Weak', color: 'text-red-400' }
  } else if (score <= 4) {
    return { score, label: 'Medium', color: 'text-yellow-400' }
  } else {
    return { score, label: 'Strong', color: 'text-green-400' }
  }
}
