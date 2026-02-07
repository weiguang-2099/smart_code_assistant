import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import BasicInfoTab from '../components/BasicInfoTab'
import ContentManagementTab from '../components/ContentManagementTab'
import PreferencesTab from '../components/PreferencesTab'

type TabType = 'basic' | 'content' | 'preferences'

export default function ProfilePage() {
  const { isAuthenticated, token } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('basic')

  const tabs = [
    { id: 'basic' as TabType, label: 'Basic Info', icon: '👤' },
    { id: 'content' as TabType, label: 'Content', icon: '📁' },
    { id: 'preferences' as TabType, label: 'Preferences', icon: '⚙' },
  ]

  if (!isAuthenticated || !token) {
    return (
      <div className="text-center py-20">
        <h2 className="text-4xl font-bold neon-text mb-4">ACCESS DENIED</h2>
        <p className="text-cyan-300 mb-8">Please authenticate to access your profile</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold neon-text tracking-wider">{'<PROFILE />'}</h2>
        <div className="h-px w-32 bg-gradient-to-r from-cyan-500 to-transparent mt-2"></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar - Tabs */}
        <div className="lg:col-span-1">
          <div className="cyber-card sticky top-6">
            <div className="p-4 border-b border-gray-700">
              <h3 className="text-lg font-semibold text-purple-400">Settings</h3>
            </div>
            <nav className="p-2 space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-left
                    ${activeTab === tab.id
                      ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                    }
                  `}
                >
                  <span className="text-xl">{tab.icon}</span>
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3">
          <div className="cyber-card">
            {/* Tab Header */}
            <div className="flex items-center gap-3 p-4 border-b border-gray-700">
              <span className="text-2xl">
                {tabs.find((t) => t.id === activeTab)?.icon}
              </span>
              <h3 className="text-xl font-semibold">
                {tabs.find((t) => t.id === activeTab)?.label}
              </h3>
            </div>

            {/* Tab Content */}
            <div className="p-6">
              {activeTab === 'basic' && <BasicInfoTab token={token} />}
              {activeTab === 'content' && <ContentManagementTab token={token} />}
              {activeTab === 'preferences' && <PreferencesTab token={token} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
