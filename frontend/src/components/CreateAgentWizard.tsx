import { useState } from 'react'
import type { Agent, AgentCreate } from '../types/agent'
import { agentService } from '../services/agentService'

interface CreateAgentWizardProps {
  open: boolean
  token: string
  onClose: () => void
  onComplete: (agent: Agent) => void
}

type WizardStep = 'basic' | 'purpose' | 'confirm'

// 可选领域列表
const DOMAIN_OPTIONS = [
  { value: 'code', label: '代码开发', icon: '💻' },
  { value: 'writing', label: '内容写作', icon: '✍️' },
  { value: 'analysis', label: '数据分析', icon: '📊' },
  { value: 'design', label: '设计创意', icon: '🎨' },
  { value: 'translation', label: '翻译', icon: '🌐' },
  { value: 'general', label: '通用助手', icon: '🤖' },
]

export default function CreateAgentWizard({
  open,
  token,
  onClose,
  onComplete,
}: CreateAgentWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>('basic')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  // AI建议相关状态
  const [suggestingName, setSuggestingName] = useState(false)
  const [suggestedNames, setSuggestedNames] = useState<string[]>([])
  const [showNameSuggestions, setShowNameSuggestions] = useState(false)

  // 表单数据
  const [formData, setFormData] = useState<AgentCreate>({
    name: '',
    domain: '',
    description: '',
    system_prompt: '',
  })

  const steps = [
    { id: 'basic' as WizardStep, label: '基础信息', icon: '1️⃣' },
    { id: 'purpose' as WizardStep, label: '目的描述', icon: '2️⃣' },
    { id: 'confirm' as WizardStep, label: '确认创建', icon: '3️⃣' },
  ]

  const updateFormData = (field: keyof AgentCreate, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const canProceed = () => {
    switch (currentStep) {
      case 'basic':
        return formData.name.trim().length > 0
      case 'purpose':
        return (formData.description ?? '').trim().length > 0
      case 'confirm':
        return true
      default:
        return false
    }
  }

  const handleNext = () => {
    const currentIndex = steps.findIndex((s) => s.id === currentStep)
    if (currentIndex < steps.length - 1) {
      setCurrentStep(steps[currentIndex + 1].id)
    }
  }

  const handleBack = () => {
    const currentIndex = steps.findIndex((s) => s.id === currentStep)
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1].id)
    }
  }

  const handleCreate = async () => {
    setCreating(true)
    setError('')

    try {
      const agent = await agentService.createAgent(token, formData)
      onComplete(agent)
      // 重置表单
      setFormData({ name: '', domain: '', description: '', system_prompt: '' })
      setCurrentStep('basic')
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const handleClose = () => {
    setFormData({ name: '', domain: '', description: '', system_prompt: '' })
    setCurrentStep('basic')
    setError('')
    setSuggestedNames([])
    setShowNameSuggestions(false)
    onClose()
  }

  // AI名称建议功能
  const handleSuggestName = async () => {
    if (!formData.domain) return

    setSuggestingName(true)
    setShowNameSuggestions(false)
    setError('')

    try {
      const response = await agentService.suggestAgentName(token, {
        domain: formData.domain,
        description: formData.description || undefined,
      })
      setSuggestedNames(response.names)
      setShowNameSuggestions(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取AI建议失败')
    } finally {
      setSuggestingName(false)
    }
  }

  const handleSelectSuggestedName = (name: string) => {
    updateFormData('name', name)
    setShowNameSuggestions(false)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="cyber-card max-w-lg w-full p-8 animate-slideUp">
        {/* 头部 */}
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-2xl font-bold neon-text-purple tracking-wider">
            {'<CREATE AGENT />'}
          </h3>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-white text-2xl transition-colors"
          >
            ×
          </button>
        </div>

        {/* 步骤指示器 */}
        <div className="flex items-center justify-between mb-8">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-full transition-all
                  ${
                    currentStep === step.id
                      ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50'
                      : steps.findIndex((s) => s.id === currentStep) > index
                      ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                      : 'bg-gray-800/50 text-gray-500 border border-gray-700'
                  }
                `}
              >
                <span>{step.icon}</span>
                <span className="text-sm font-medium">{step.label}</span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`w-8 h-0.5 mx-2 ${
                    steps.findIndex((s) => s.id === currentStep) > index
                      ? 'bg-green-500/50'
                      : 'bg-gray-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-4 p-3 border border-red-500/50 rounded bg-red-500/10 flex justify-between items-center">
            <p className="text-sm text-red-400">{error}</p>
            <button onClick={() => setError('')} className="text-red-400 hover:text-white">
              ×
            </button>
          </div>
        )}

        {/* 步骤内容 */}
        <div className="min-h-[200px]">
          {/* Step 1: 基础信息 */}
          {currentStep === 'basic' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-purple-300 mb-2">
                  智能体名称 *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => updateFormData('name', e.target.value)}
                  className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded
                             text-gray-100 placeholder-gray-500 focus:border-purple-500
                             focus:ring-2 focus:ring-purple-500/20 transition-all"
                  placeholder="给智能体起个名字..."
                  maxLength={100}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-purple-300 mb-2">
                  主要领域
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {DOMAIN_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => updateFormData('domain', option.value)}
                      className={`
                        px-3 py-2 rounded text-sm transition-all flex items-center gap-1.5
                        ${
                          formData.domain === option.value
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                            : 'bg-gray-800/50 text-gray-400 border border-gray-700 hover:border-gray-600'
                        }
                      `}
                    >
                      <span>{option.icon}</span>
                      <span>{option.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* AI名称建议 */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleSuggestName}
                  disabled={!formData.domain || suggestingName}
                  className={`
                    w-full py-2.5 rounded flex items-center justify-center gap-2 text-sm
                    transition-all border
                    ${
                      formData.domain
                        ? 'bg-gradient-to-r from-purple-500/20 to-cyan-500/20 border-purple-500/50 text-purple-300 hover:border-purple-400 hover:text-purple-200'
                        : 'bg-gray-800/30 border-gray-700 text-gray-500 cursor-not-allowed'
                    }
                  `}
                >
                  {suggestingName ? (
                    <>
                      <span className="animate-spin">◌</span>
                      <span>AI思考中...</span>
                    </>
                  ) : (
                    <>
                      <span>✨</span>
                      <span>AI帮我想个名称</span>
                    </>
                  )}
                </button>
                {!formData.domain && (
                  <p className="text-xs text-gray-500 mt-1 text-center">
                    请先选择一个领域
                  </p>
                )}

                {/* 建议的名称列表 */}
                {showNameSuggestions && suggestedNames.length > 0 && (
                  <div className="mt-3 p-3 bg-gray-800/50 rounded border border-purple-500/30">
                    <p className="text-xs text-purple-300 mb-2 flex items-center gap-1">
                      <span>💡</span>
                      <span>AI推荐的名称：</span>
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {suggestedNames.map((name, index) => (
                        <button
                          key={index}
                          type="button"
                          onClick={() => handleSelectSuggestedName(name)}
                          className="px-3 py-1.5 text-sm bg-purple-500/20 text-purple-200
                                     border border-purple-500/30 rounded-full
                                     hover:bg-purple-500/30 hover:border-purple-400
                                     transition-all"
                        >
                          {name}
                        </button>
                      ))}
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      点击名称即可使用
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 2: 目的描述 */}
          {currentStep === 'purpose' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-purple-300 mb-2">
                  详细描述 *
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => updateFormData('description', e.target.value)}
                  className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded
                             text-gray-100 placeholder-gray-500 focus:border-purple-500
                             focus:ring-2 focus:ring-purple-500/20 transition-all resize-none"
                  placeholder="描述这个智能体的用途、特点..."
                  rows={4}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-purple-300 mb-2">
                  系统提示词（可选）
                </label>
                <textarea
                  value={formData.system_prompt}
                  onChange={(e) => updateFormData('system_prompt', e.target.value)}
                  className="w-full px-4 py-3 bg-gray-900/50 border border-purple-500/30 rounded
                             text-gray-100 placeholder-gray-500 focus:border-purple-500
                             focus:ring-2 focus:ring-purple-500/20 transition-all resize-none font-mono text-sm"
                  placeholder="你是一个专业的助手..."
                  rows={4}
                />
                <p className="text-xs text-gray-500 mt-1">
                  定义智能体的行为方式和角色设定
                </p>
              </div>
            </div>
          )}

          {/* Step 3: 确认创建 */}
          {currentStep === 'confirm' && (
            <div className="space-y-4">
              <div className="p-4 bg-gray-800/50 rounded border border-gray-700">
                <h4 className="text-sm font-medium text-cyan-300 mb-3">配置预览</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">名称：</span>
                    <span className="text-gray-200">{formData.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">领域：</span>
                    <span className="text-gray-200">
                      {DOMAIN_OPTIONS.find((d) => d.value === formData.domain)?.label || '未设置'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">描述：</span>
                    <span className="text-gray-200 text-right max-w-[200px] truncate">
                      {formData.description}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-center text-gray-400 text-sm">
                确认创建智能体「{formData.name}」？
              </p>
            </div>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex gap-4 mt-6">
          {currentStep !== 'basic' && (
            <button
              onClick={handleBack}
              className="flex-1 cyber-btn py-3"
              disabled={creating}
            >
              上一步
            </button>
          )}

          {currentStep !== 'confirm' ? (
            <button
              onClick={handleNext}
              disabled={!canProceed()}
              className="flex-1 cyber-btn py-3 disabled:opacity-30 disabled:cursor-not-allowed"
              style={{
                borderColor: canProceed() ? 'var(--color-neon-green)' : undefined,
                color: canProceed() ? 'var(--color-neon-green)' : undefined,
              }}
            >
              下一步
            </button>
          ) : (
            <button
              onClick={handleCreate}
              disabled={creating}
              className="flex-1 cyber-btn py-3 disabled:opacity-50"
              style={{ borderColor: 'var(--color-neon-green)', color: 'var(--color-neon-green)' }}
            >
              {creating ? '创建中...' : '确认创建'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
