import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type AnalysisType = 'structure' | 'smells' | 'complexity' | 'security' | 'all_basic'
type GraphQueryType = 'search' | 'dependencies' | 'impact' | 'paths'

interface AnalysisResult {
  type: string
  success: boolean
  result: string
  error?: string
}

interface FullAnalysisResponse {
  structure?: string
  smells?: string
  complexity?: string
  security?: string
  graph_built: boolean
  graph_stats?: { nodes: number; relationships: number; error?: string }
  overall_score: number
  summary: string
  recommendations: string[]
}

interface GraphNode {
  id: string
  label: string
  type: string
  color: string
  module: string
  class?: string
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface GraphEdge {
  id: string
  source: string
  target: string
  label: string
  color: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: { node_count: number; edge_count: number }
}

export default function CodeAnalysisPage() {
  const { token, isAuthenticated } = useAuth()

  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 基础分析结果
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([])

  // 完整分析结果
  const [fullAnalysis, setFullAnalysis] = useState<FullAnalysisResponse | null>(null)

  // GraphRAG 查询
  const [graphQuery, setGraphQuery] = useState('')
  const [graphQueryType, setGraphQueryType] = useState<GraphQueryType>('search')
  const [graphResult, setGraphResult] = useState<string>('')
  const [graphLoading, setGraphLoading] = useState(false)

  // 图谱可视化
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [graphVizLoading, setGraphVizLoading] = useState(false)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [scale, setScale] = useState(1)
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  // 分析选项
  const [enableGraph, setEnableGraph] = useState(true)
  const [activeTab, setActiveTab] = useState<'editor' | 'results' | 'graph' | 'visualize'>('editor')

  const runBasicAnalysis = async () => {
    if (!code.trim() || !token) return

    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/api/v1/code-analysis/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          code,
          language,
          analysis_types: ['all_basic'],
        }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      setAnalysisResults(data.results)
      setActiveTab('results')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const runFullAnalysis = async () => {
    if (!code.trim() || !token) return

    setLoading(true)
    setError('')
    setFullAnalysis(null)

    try {
      const response = await fetch(`${API_URL}/api/v1/code-analysis/full-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          code,
          language,
          module_path: 'editor_input',
          enable_graph: enableGraph,
          enable_basic: true,
        }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      setFullAnalysis(data)
      setActiveTab('results')

      // 如果构建了图谱，自动加载可视化
      if (data.graph_built) {
        loadGraphVisualization()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const runGraphQuery = async () => {
    if (!graphQuery.trim() || !token) return

    setGraphLoading(true)
    setGraphResult('')

    try {
      const response = await fetch(`${API_URL}/api/v1/code-analysis/graph/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: graphQuery,
          query_type: graphQueryType,
          project_id: 1,
        }),
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      setGraphResult(data.result || JSON.stringify(data, null, 2))
    } catch (err) {
      setGraphResult(`❌ 查询失败: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setGraphLoading(false)
    }
  }

  const loadGraphVisualization = async () => {
    if (!token) return

    setGraphVizLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/v1/code-graph/visualize?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()

      if (data.success && data.nodes.length > 0) {
        // 为节点分配初始位置（圆形布局）
        const centerX = 400
        const centerY = 300
        const radius = Math.min(250, 50 * Math.sqrt(data.nodes.length))

        const nodesWithPositions = data.nodes.map((node: GraphNode, i: number) => {
          const angle = (2 * Math.PI * i) / data.nodes.length
          return {
            ...node,
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
            vx: 0,
            vy: 0,
          }
        })

        setGraphData({ ...data, nodes: nodesWithPositions })
      } else {
        setGraphData(null)
      }
    } catch (err) {
      console.error('Failed to load graph:', err)
      setGraphData(null)
    } finally {
      setGraphVizLoading(false)
    }
  }

  // Canvas 绘制
  const drawGraph = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || !graphData) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height

    // 清空画布
    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, width, height)

    // 应用变换
    ctx.save()
    ctx.translate(offset.x, offset.y)
    ctx.scale(scale, scale)

    // 绘制边
    graphData.edges.forEach((edge) => {
      const source = graphData.nodes.find((n) => n.id === edge.source)
      const target = graphData.nodes.find((n) => n.id === edge.target)

      if (source && target && source.x && source.y && target.x && target.y) {
        ctx.beginPath()
        ctx.moveTo(source.x, source.y)
        ctx.lineTo(target.x, target.y)
        ctx.strokeStyle = edge.color + '60' // 半透明
        ctx.lineWidth = 1.5
        ctx.stroke()

        // 绘制箭头
        const angle = Math.atan2(target.y - source.y, target.x - source.x)
        const arrowLen = 8
        const arrowX = target.x - 20 * Math.cos(angle)
        const arrowY = target.y - 20 * Math.sin(angle)

        ctx.beginPath()
        ctx.moveTo(arrowX, arrowY)
        ctx.lineTo(
          arrowX - arrowLen * Math.cos(angle - Math.PI / 6),
          arrowY - arrowLen * Math.sin(angle - Math.PI / 6)
        )
        ctx.lineTo(
          arrowX - arrowLen * Math.cos(angle + Math.PI / 6),
          arrowY - arrowLen * Math.sin(angle + Math.PI / 6)
        )
        ctx.closePath()
        ctx.fillStyle = edge.color + '80'
        ctx.fill()
      }
    })

    // 绘制节点
    graphData.nodes.forEach((node) => {
      if (node.x === undefined || node.y === undefined) return

      const isSelected = selectedNode?.id === node.id
      const radius = isSelected ? 20 : 15

      // 节点光晕
      if (isSelected) {
        const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, 30)
        gradient.addColorStop(0, node.color + '40')
        gradient.addColorStop(1, 'transparent')
        ctx.beginPath()
        ctx.arc(node.x, node.y, 30, 0, Math.PI * 2)
        ctx.fillStyle = gradient
        ctx.fill()
      }

      // 节点圆形
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2)
      ctx.fillStyle = isSelected ? node.color : node.color + 'cc'
      ctx.fill()
      ctx.strokeStyle = '#ffffff30'
      ctx.lineWidth = 1
      ctx.stroke()

      // 节点标签
      ctx.fillStyle = '#ffffff'
      ctx.font = '10px monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'

      // 截断过长的标签
      const label = node.label.length > 10 ? node.label.slice(0, 10) + '..' : node.label
      ctx.fillText(label, node.x, node.y + radius + 12)
    })

    ctx.restore()
  }, [graphData, offset, scale, selectedNode])

  // 重绘
  useEffect(() => {
    drawGraph()
  }, [drawGraph])

  // 鼠标交互
  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas || !graphData) return

    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - offset.x) / scale
    const y = (e.clientY - rect.top - offset.y) / scale

    // 检查是否点击了节点
    const clickedNode = graphData.nodes.find((node) => {
      if (node.x === undefined || node.y === undefined) return false
      const dist = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2)
      return dist < 15
    })

    if (clickedNode) {
      setSelectedNode(clickedNode)
    } else {
      setSelectedNode(null)
      setIsDragging(true)
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y })
    }
  }

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) {
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      })
    }
  }

  const handleCanvasMouseUp = () => {
    setIsDragging(false)
  }

  const handleCanvasWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    setScale((s) => Math.max(0.3, Math.min(3, s * delta)))
  }

  const renderAnalysisResult = (result: string) => {
    return result.split('\n').map((line, i) => {
      if (line.startsWith('━')) {
        return <div key={i} className="border-t border-gray-700 my-2" />
      }
      if (line.includes('•')) {
        return (
          <div key={i} className="text-gray-300 text-sm pl-2 py-0.5">
            {line}
          </div>
        )
      }
      if (line.includes('⚠️') || line.includes('🔴') || line.includes('🟠')) {
        return (
          <div key={i} className="text-yellow-400 text-sm pl-2 py-0.5">
            {line}
          </div>
        )
      }
      if (line.includes('✅') || line.includes('🟢')) {
        return (
          <div key={i} className="text-green-400 text-sm pl-2 py-0.5">
            {line}
          </div>
        )
      }
      return (
        <div key={i} className="text-gray-300 text-sm">
          {line}
        </div>
      )
    })
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    return 'text-red-400'
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-6xl mb-4">🔐</div>
          <h3 className="text-xl font-semibold text-gray-300 mb-2">需要登录</h3>
          <p className="text-gray-500">请先登录以使用代码分析功能</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold neon-text">代码分析</h1>
          <p className="text-gray-400 text-sm mt-1">
            基础分析 + GraphRAG 知识图谱
          </p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="px-3 py-2 bg-gray-900/50 border border-cyan-500/30 rounded-lg text-gray-300"
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-400">
            <input
              type="checkbox"
              checked={enableGraph}
              onChange={(e) => setEnableGraph(e.target.checked)}
              className="rounded border-gray-600 bg-gray-900"
            />
            构建知识图谱
          </label>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-700">
        {[
          { id: 'editor', label: '代码编辑' },
          { id: 'results', label: '分析结果' },
          { id: 'visualize', label: '图谱可视化' },
          { id: 'graph', label: '图谱查询' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id as typeof activeTab)
              if (tab.id === 'visualize' && !graphData) {
                loadGraphVisualization()
              }
            }}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? 'text-cyan-400 border-cyan-400'
                : 'text-gray-400 border-transparent hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 border border-red-500/50 rounded-lg bg-red-500/10">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Editor Tab */}
      {activeTab === 'editor' && (
        <div className="space-y-4">
          <div className="relative">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="粘贴或输入代码..."
              className="w-full h-96 px-4 py-3 bg-gray-900/50 border border-cyan-500/30 rounded-lg
                         text-gray-100 font-mono text-sm resize-none
                         focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20"
            />
            <div className="absolute bottom-3 right-3 text-xs text-gray-500">
              {code.split('\n').length} 行
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={runBasicAnalysis}
              disabled={loading || !code.trim()}
              className="px-6 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30
                         hover:bg-cyan-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loading ? '分析中...' : '基础分析'}
            </button>
            <button
              onClick={runFullAnalysis}
              disabled={loading || !code.trim()}
              className="px-6 py-2 rounded-lg bg-purple-500/20 text-purple-400 border border-purple-500/30
                         hover:bg-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loading ? '分析中...' : '完整分析 + GraphRAG'}
            </button>
          </div>
        </div>
      )}

      {/* Results Tab */}
      {activeTab === 'results' && (
        <div className="space-y-6">
          {fullAnalysis && (
            <div className="cyber-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-100">综合评估</h3>
                <div className={`text-3xl font-bold ${getScoreColor(fullAnalysis.overall_score)}`}>
                  {fullAnalysis.overall_score}
                </div>
              </div>
              <p className="text-gray-400 mb-4">{fullAnalysis.summary}</p>

              {fullAnalysis.recommendations.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-2">改进建议:</h4>
                  <ul className="space-y-1">
                    {fullAnalysis.recommendations.map((rec, i) => (
                      <li key={i} className="text-sm text-gray-400 flex items-start gap-2">
                        <span className="text-cyan-400">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {fullAnalysis.graph_built && fullAnalysis.graph_stats && (
                <div className="mt-4 pt-4 border-t border-gray-700">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium text-gray-300">知识图谱:</h4>
                    <button
                      onClick={() => {
                        setActiveTab('visualize')
                        loadGraphVisualization()
                      }}
                      className="text-xs text-cyan-400 hover:text-cyan-300"
                    >
                      查看图谱 →
                    </button>
                  </div>
                  <div className="flex gap-4 text-sm mt-2">
                    <span className="text-gray-400">
                      节点: <span className="text-cyan-400">{fullAnalysis.graph_stats.nodes}</span>
                    </span>
                    <span className="text-gray-400">
                      关系: <span className="text-purple-400">{fullAnalysis.graph_stats.relationships}</span>
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {fullAnalysis?.structure && (
            <div className="cyber-card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-3">📊 结构分析</h3>
              <div className="bg-gray-900/50 rounded-lg p-4">
                {renderAnalysisResult(fullAnalysis.structure)}
              </div>
            </div>
          )}

          {fullAnalysis?.security && (
            <div className="cyber-card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-3">🔒 安全检查</h3>
              <div className="bg-gray-900/50 rounded-lg p-4">
                {renderAnalysisResult(fullAnalysis.security)}
              </div>
            </div>
          )}

          {!analysisResults.length && !fullAnalysis && (
            <div className="text-center py-12 text-gray-500">
              <div className="text-4xl mb-4">📋</div>
              <p>还没有分析结果</p>
              <p className="text-sm mt-2">在"代码编辑"中输入代码并点击分析</p>
            </div>
          )}
        </div>
      )}

      {/* Graph Visualization Tab */}
      {activeTab === 'visualize' && (
        <div className="space-y-4">
          <div className="cyber-card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-100">代码知识图谱</h3>
              <div className="flex items-center gap-4">
                {graphData && (
                  <span className="text-sm text-gray-400">
                    {graphData.stats.node_count} 节点 · {graphData.stats.edge_count} 关系
                  </span>
                )}
                <button
                  onClick={loadGraphVisualization}
                  disabled={graphVizLoading}
                  className="px-3 py-1 text-xs rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30
                             hover:bg-cyan-500/30 disabled:opacity-50"
                >
                  {graphVizLoading ? '加载中...' : '刷新'}
                </button>
              </div>
            </div>

            {/* Canvas */}
            <div className="relative border border-gray-700 rounded-lg overflow-hidden bg-gray-900/50">
              {graphVizLoading ? (
                <div className="flex items-center justify-center h-[500px]">
                  <div className="animate-spin text-4xl text-cyan-400">◌</div>
                </div>
              ) : graphData && graphData.nodes.length > 0 ? (
                <canvas
                  ref={canvasRef}
                  width={800}
                  height={500}
                  className="w-full cursor-grab active:cursor-grabbing"
                  onMouseDown={handleCanvasMouseDown}
                  onMouseMove={handleCanvasMouseMove}
                  onMouseUp={handleCanvasMouseUp}
                  onMouseLeave={handleCanvasMouseUp}
                  onWheel={handleCanvasWheel}
                />
              ) : (
                <div className="flex items-center justify-center h-[500px] text-gray-500">
                  <div className="text-center">
                    <div className="text-4xl mb-4">🕸️</div>
                    <p>暂无图谱数据</p>
                    <p className="text-sm mt-2">请先分析代码构建知识图谱</p>
                  </div>
                </div>
              )}

              {/* Selected Node Info */}
              {selectedNode && (
                <div className="absolute bottom-4 left-4 p-3 bg-gray-900/90 border border-gray-700 rounded-lg max-w-xs">
                  <div className="flex items-center gap-2 mb-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: selectedNode.color }}
                    />
                    <span className="font-medium text-gray-100">{selectedNode.label}</span>
                  </div>
                  <div className="text-xs text-gray-400 space-y-1">
                    <div>类型: {selectedNode.type}</div>
                    <div>模块: {selectedNode.module}</div>
                    {selectedNode.class && <div>类: {selectedNode.class}</div>}
                  </div>
                </div>
              )}

              {/* Zoom Controls */}
              <div className="absolute top-4 right-4 flex flex-col gap-2">
                <button
                  onClick={() => setScale((s) => Math.min(3, s * 1.2))}
                  className="w-8 h-8 flex items-center justify-center bg-gray-800 border border-gray-700
                             rounded text-gray-300 hover:text-white"
                >
                  +
                </button>
                <button
                  onClick={() => setScale((s) => Math.max(0.3, s * 0.8))}
                  className="w-8 h-8 flex items-center justify-center bg-gray-800 border border-gray-700
                             rounded text-gray-300 hover:text-white"
                >
                  −
                </button>
                <button
                  onClick={() => {
                    setScale(1)
                    setOffset({ x: 0, y: 0 })
                  }}
                  className="w-8 h-8 flex items-center justify-center bg-gray-800 border border-gray-700
                             rounded text-gray-300 hover:text-white text-xs"
                >
                  ⌂
                </button>
              </div>
            </div>

            {/* Legend */}
            {graphData && (
              <div className="flex items-center gap-6 mt-4 text-xs text-gray-400">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-cyan-400" />
                  <span>函数</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-purple-500" />
                  <span>类</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span>模块</span>
                </div>
                <div className="text-gray-500 ml-4">
                  拖拽移动 · 滚轮缩放 · 点击查看详情
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Graph Query Tab */}
      {activeTab === 'graph' && (
        <div className="space-y-4">
          <div className="cyber-card p-6">
            <h3 className="text-lg font-semibold text-gray-100 mb-4">图谱查询</h3>

            <div className="flex gap-4 mb-4">
              <select
                value={graphQueryType}
                onChange={(e) => setGraphQueryType(e.target.value as GraphQueryType)}
                className="px-3 py-2 bg-gray-900/50 border border-cyan-500/30 rounded-lg text-gray-300"
              >
                <option value="search">语义搜索</option>
                <option value="dependencies">依赖查询</option>
                <option value="impact">影响分析</option>
                <option value="paths">路径查找</option>
              </select>

              <input
                type="text"
                value={graphQuery}
                onChange={(e) => setGraphQuery(e.target.value)}
                placeholder={
                  graphQueryType === 'search'
                    ? '输入自然语言查询，如：处理用户认证的函数'
                    : graphQueryType === 'dependencies'
                    ? '输入函数名或类名'
                    : graphQueryType === 'impact'
                    ? '输入要分析的实体名称'
                    : '输入 source,target（用逗号分隔）'
                }
                className="flex-1 px-4 py-2 bg-gray-900/50 border border-cyan-500/30 rounded-lg
                           text-gray-100 placeholder-gray-500"
              />

              <button
                onClick={runGraphQuery}
                disabled={graphLoading || !graphQuery.trim()}
                className="px-6 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30
                           hover:bg-cyan-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {graphLoading ? '查询中...' : '查询'}
              </button>
            </div>

            {graphResult && (
              <div className="bg-gray-900/50 rounded-lg p-4">
                <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                  {graphResult}
                </pre>
              </div>
            )}
          </div>

          <div className="cyber-card p-6">
            <h3 className="text-lg font-semibold text-gray-100 mb-4">查询类型说明</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-900/30 rounded-lg">
                <h4 className="text-cyan-400 font-medium mb-2">🔎 语义搜索</h4>
                <p className="text-sm text-gray-400">
                  使用自然语言搜索代码实体，如"处理用户登录的函数"
                </p>
              </div>
              <div className="p-4 bg-gray-900/30 rounded-lg">
                <h4 className="text-purple-400 font-medium mb-2">🔗 依赖查询</h4>
                <p className="text-sm text-gray-400">
                  查询函数/类的调用关系，找出谁调用了它以及它调用了谁
                </p>
              </div>
              <div className="p-4 bg-gray-900/30 rounded-lg">
                <h4 className="text-yellow-400 font-medium mb-2">🎯 影响分析</h4>
                <p className="text-sm text-gray-400">
                  分析修改某个函数会影响哪些其他代码
                </p>
              </div>
              <div className="p-4 bg-gray-900/30 rounded-lg">
                <h4 className="text-green-400 font-medium mb-2">🛤️ 路径查找</h4>
                <p className="text-sm text-gray-400">
                  查找两个函数之间的调用路径
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
