import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import AudioUploader from './components/AudioUploader'
import AnalysisResults from './components/AnalysisResults'
import LoadingAnalysis from './components/LoadingAnalysis'
import LiveVoiceAnalyzer from './components/LiveVoiceAnalyzer'
import Header from './components/Header'
import BackgroundEffects from './components/BackgroundEffects'
import { Upload, Mic } from 'lucide-react'

const API_BASE = '/api/v1'

function App() {
  const [mode, setMode] = useState('live') // Live режим по умолчанию
  const [stage, setStage] = useState('upload')
  const [analysisResult, setAnalysisResult] = useState(null)
  const [error, setError] = useState(null)

  const handleUpload = async (file) => {
    setError(null)
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const uploadRes = await fetch(`${API_BASE}/upload-audio`, {
        method: 'POST',
        body: formData,
      })
      
      if (!uploadRes.ok) {
        const err = await uploadRes.json()
        throw new Error(err.detail || 'Ошибка загрузки')
      }
      
      const uploadData = await uploadRes.json()
      setStage('analyzing')
      
      const analysisRes = await fetch(
        `${API_BASE}/analyze-voice?session_id=${uploadData.session_id}`,
        { method: 'POST' }
      )
      
      if (!analysisRes.ok) {
        const err = await analysisRes.json()
        throw new Error(err.detail || 'Ошибка анализа')
      }
      
      const result = await analysisRes.json()
      setAnalysisResult(result)
      setStage('results')
      
    } catch (err) {
      setError(err.message)
      setStage('upload')
    }
  }

  const handleReset = () => {
    setStage('upload')
    setMode('upload')
    setAnalysisResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen">
      <BackgroundEffects />
      
      <Header onReset={handleReset} showReset={stage !== 'upload'} />
      
      <main className="container mx-auto px-4 py-8">
        {/* Переключатель */}
        {stage === 'upload' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-center gap-2 mb-6"
          >
            <button
              onClick={() => setMode('live')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                mode === 'live'
                  ? 'bg-primary text-white shadow-md shadow-primary/20'
                  : 'bg-white text-slate-600 border border-slate-200 hover:border-primary/30'
              }`}
            >
              <Mic className="w-4 h-4" />
              Live анализ
            </button>
            <button
              onClick={() => setMode('upload')}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                mode === 'upload'
                  ? 'bg-primary text-white shadow-md shadow-primary/20'
                  : 'bg-white text-slate-600 border border-slate-200 hover:border-primary/30'
              }`}
            >
              <Upload className="w-4 h-4" />
              Загрузить файл
            </button>
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {stage === 'upload' && mode === 'live' && (
            <motion.div
              key="live"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <LiveVoiceAnalyzer />
            </motion.div>
          )}
          
          {stage === 'upload' && mode === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <AudioUploader onUpload={handleUpload} error={error} />
            </motion.div>
          )}
          
          {stage === 'analyzing' && (
            <motion.div
              key="analyzing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <LoadingAnalysis />
            </motion.div>
          )}
          
          {stage === 'results' && analysisResult && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <AnalysisResults data={analysisResult} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

export default App
