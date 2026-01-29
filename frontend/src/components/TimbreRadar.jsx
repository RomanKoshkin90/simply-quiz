import { motion } from 'framer-motion'
import { useMemo } from 'react'
import { Info } from 'lucide-react'

// Пояснения для каждой метрики
const explanations = {
  brightness: {
    label: 'Яркость (HNR)',
    low: 'Мягкий, бархатный тембр — отлично для баллад и джаза',
    mid: 'Сбалансированный тембр — универсален для большинства стилей',
    high: 'Звонкий, пронзительный голос — идеален для поп и рок музыки',
    tip: 'Чем выше значение, тем чище и звонче звучит голос'
  },
  stability: {
    label: 'Стабильность',
    low: 'Голос "плавает" — поработай над дыханием и опорой',
    mid: 'Хороший контроль — продолжай практиковаться!',
    high: 'Отличная стабильность — профессиональный уровень!',
    tip: 'Показывает, насколько ровно ты держишь ноты'
  },
  power: {
    label: 'Сила подачи',
    low: 'Тихое пение — попробуй петь увереннее и громче',
    mid: 'Хорошая громкость — голос слышен чётко',
    high: 'Мощный голос — отлично для концертов!',
    tip: 'Средняя громкость твоего голоса во время записи'
  },
  resonance: {
    label: 'Резонанс (F1)',
    low: 'Закрытый звук — попробуй открыть рот шире',
    mid: 'Нормальный резонанс — хорошая артикуляция',
    high: 'Открытый, полётный голос — звук хорошо проецируется',
    tip: 'Как хорошо голос резонирует в голове и груди'
  },
  dynamics: {
    label: 'Динамика',
    low: 'Монотонное пение — добавь эмоций и контрастов!',
    mid: 'Есть динамические изменения — неплохо!',
    high: 'Богатая динамика — выразительное исполнение!',
    tip: 'Насколько разнообразно ты меняешь громкость'
  }
}

function TimbreRadar({ features }) {
  const metrics = useMemo(() => {
    if (!features) return []
    
    const normalize = (val, min, max) => {
      if (val == null) return 0
      return Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100))
    }

    return [
      { 
        key: 'brightness',
        label: 'Яркость (HNR)', 
        value: normalize(features.hnr, 5, 30), 
        raw: features.hnr?.toFixed(1), 
        unit: 'dB' 
      },
      { 
        key: 'stability',
        label: 'Стабильность', 
        value: normalize(100 - (features.jitter || 0) * 1000, 0, 100), 
        raw: features.jitter ? (features.jitter * 100).toFixed(2) : null, 
        unit: '%' 
      },
      { 
        key: 'power',
        label: 'Сила подачи', 
        value: normalize(features.loudness_mean, 0, 1), 
        raw: features.loudness_mean?.toFixed(2), 
        unit: '' 
      },
      { 
        key: 'resonance',
        label: 'Резонанс (F1)', 
        value: normalize(features.f1_mean, 200, 1000), 
        raw: features.f1_mean?.toFixed(0), 
        unit: 'Hz' 
      },
      { 
        key: 'dynamics',
        label: 'Динамика', 
        value: normalize(features.spectral_flux, 0, 0.15), 
        raw: features.spectral_flux?.toFixed(3), 
        unit: '' 
      },
    ]
  }, [features])

  const getLevel = (value) => {
    if (value < 33) return 'low'
    if (value < 66) return 'mid'
    return 'high'
  }

  const getLevelColor = (value) => {
    if (value < 33) return 'text-amber-600'
    if (value < 66) return 'text-blue-600'
    return 'text-green-600'
  }

  if (!features || metrics.length === 0) {
    return <p className="text-slate-400 text-center py-6 text-sm">Нет данных</p>
  }

  return (
    <div className="space-y-4">
      {metrics.map((m, i) => {
        const exp = explanations[m.key]
        const level = getLevel(m.value)
        return (
          <motion.div
            key={m.key}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
            className="group"
          >
            <div className="flex justify-between text-sm mb-1">
              <span className="text-slate-600 font-medium">{m.label}</span>
              <span className="font-mono text-primary">
                {m.raw != null ? `${m.raw}${m.unit}` : '—'}
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden mb-1">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                initial={{ width: 0 }}
                animate={{ width: `${m.value}%` }}
                transition={{ duration: 0.5, delay: 0.1 + i * 0.08 }}
              />
            </div>
            {/* Пояснение */}
            <div className="flex items-start gap-1.5">
              <Info className="w-3 h-3 text-slate-400 mt-0.5 flex-shrink-0" />
              <p className={`text-xs ${getLevelColor(m.value)}`}>
                {exp[level]}
              </p>
            </div>
          </motion.div>
        )
      })}
      
    </div>
  )
}

export default TimbreRadar
