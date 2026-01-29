import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'

const STEPS = [
  { text: 'Обработка аудио', icon: '🎧' },
  { text: 'Извлечение pitch', icon: '🎵' },
  { text: 'Анализ тембра', icon: '🎭' },
  { text: 'Поиск артистов', icon: '⭐' },
]

function LoadingAnalysis() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setStep(s => (s < STEPS.length - 1 ? s + 1 : s))
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="max-w-md mx-auto mt-16 text-center">
      {/* Визуализатор */}
      <div className="flex items-end justify-center gap-1 h-16 mb-8">
        {[...Array(8)].map((_, i) => (
          <motion.div
            key={i}
            className="w-2 rounded-full bg-primary"
            animate={{ height: [16, 40 + Math.random() * 20, 16] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.08 }}
          />
        ))}
      </div>

      <h2 className="font-display font-semibold text-xl text-slate-800 mb-2">
        Анализируем голос
      </h2>
      <p className="text-slate-500 mb-8">Несколько секунд...</p>

      {/* Шаги */}
      <div className="space-y-2">
        {STEPS.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: i <= step ? 1 : 0.4, x: 0 }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl ${
              i === step ? 'bg-primary/10 border border-primary/20' : 'bg-white border border-slate-100'
            }`}
          >
            <span>{s.icon}</span>
            <span className={i <= step ? 'text-slate-700' : 'text-slate-400'}>{s.text}</span>
            {i < step && <span className="ml-auto text-green-500">✓</span>}
            {i === step && (
              <div className="ml-auto w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
          </motion.div>
        ))}
      </div>
    </div>
  )
}

export default LoadingAnalysis
