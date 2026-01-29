import { motion } from 'framer-motion'
import { useMemo } from 'react'

const NOTES = [
  { note: 'C2', hz: 65 },
  { note: 'C3', hz: 131 },
  { note: 'C4', hz: 262 },
  { note: 'C5', hz: 523 },
  { note: 'C6', hz: 1047 },
]

function VocalRangeChart({ minHz, maxHz, medianHz }) {
  const CHART_MIN = 60, CHART_MAX = 1100

  const hzToPercent = (hz) => {
    const logMin = Math.log2(CHART_MIN)
    const logMax = Math.log2(CHART_MAX)
    return ((Math.log2(hz) - logMin) / (logMax - logMin)) * 100
  }

  const range = useMemo(() => ({
    left: hzToPercent(minHz),
    width: hzToPercent(maxHz) - hzToPercent(minHz),
    median: hzToPercent(medianHz),
  }), [minHz, maxHz, medianHz])

  return (
    <div className="relative pt-6 pb-10">
      {/* Фон */}
      <div className="h-10 rounded-lg bg-slate-100 relative overflow-hidden">
        {/* Диапазон пользователя */}
        <motion.div
          className="absolute top-0 h-full rounded-md bg-gradient-to-r from-primary to-accent"
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: `${range.width}%`, opacity: 1, left: `${range.left}%` }}
          transition={{ duration: 0.6, delay: 0.2 }}
        />

        {/* Медиана */}
        <motion.div
          className="absolute top-0 h-full w-0.5 bg-white"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, left: `${range.median}%` }}
          transition={{ delay: 0.5 }}
        >
          <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-xs text-slate-600 font-mono whitespace-nowrap">
            {Math.round(medianHz)} Hz
          </div>
        </motion.div>
      </div>

      {/* Метки min/max */}
      <div className="absolute text-xs text-slate-500 font-mono" style={{ left: `${range.left}%`, bottom: 0 }}>
        {Math.round(minHz)}
      </div>
      <div className="absolute text-xs text-slate-500 font-mono -translate-x-full" style={{ left: `${range.left + range.width}%`, bottom: 0 }}>
        {Math.round(maxHz)}
      </div>

      {/* Шкала нот */}
      <div className="absolute bottom-0 left-0 right-0">
        {NOTES.map(n => (
          <div
            key={n.note}
            className="absolute flex flex-col items-center"
            style={{ left: `${hzToPercent(n.hz)}%`, transform: 'translateX(-50%)' }}
          >
            <div className="w-px h-2 bg-slate-300" />
            <span className="text-[10px] text-slate-400 mt-0.5">{n.note}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default VocalRangeChart
