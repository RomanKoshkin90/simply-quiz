import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, RotateCcw, Mic2, Activity, Gauge, Music, Info, AlertCircle, User, Lock } from 'lucide-react'
import Spectrogram from './Spectrogram'
import ArtistCard from './ArtistCard'
import SongCard from './SongCard'
import { sendToTelegram } from '../utils/telegram'
import { ymReachGoal } from '../hooks/useYandexMetrika'

// Русские названия нот
const NOTE_NAMES_RU = {
  'C': 'До', 'C#': 'До#', 'D': 'Ре', 'D#': 'Ре#',
  'E': 'Ми', 'F': 'Фа', 'F#': 'Фа#', 'G': 'Соль',
  'G#': 'Соль#', 'A': 'Ля', 'A#': 'Ля#', 'B': 'Си'
}

// Преобразование Hz в ноту (русский формат)
const hzToNote = (frequency) => {
  if (frequency <= 0 || !isFinite(frequency)) return { note: '—', noteRu: '—', octave: '', full: '—', fullRu: '—' }
  const A4 = 440
  const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  const semitones = 12 * Math.log2(frequency / A4)
  const totalSemitones = Math.round(semitones) + 9 + (4 * 12)
  const octave = Math.floor(totalSemitones / 12)
  const noteIndex = ((totalSemitones % 12) + 12) % 12
  const note = notes[noteIndex]
  const noteRu = NOTE_NAMES_RU[note]
  return { 
    note, 
    noteRu, 
    octave: String(octave), 
    full: `${note}${octave}`,
    fullRu: `${noteRu}${octave}`
  }
}

// Определение типа голоса по диапазону
const detectVoiceType = (minHz, maxHz) => {
  const medianHz = (minHz + maxHz) / 2

  if (medianHz < 130) return { type: 'bass', name: 'Бас', desc: 'Самый низкий голос' }
  if (medianHz < 165) return { type: 'baritone', name: 'Баритон', desc: 'Средний низкий голос' }
  if (medianHz < 260) return { type: 'tenor', name: 'Тенор', desc: 'Высокий голос' }
  if (medianHz < 350) return { type: 'alto', name: 'Альт', desc: 'Низкий голос' }
  if (medianHz < 440) return { type: 'mezzo-soprano', name: 'Меццо-сопрано', desc: 'Средний голос' }
  return { type: 'soprano', name: 'Сопрано', desc: 'Высокий голос' }
}

// Оценка тембра на основе записи
const analyzeTimbr = (stats) => {
  // Упрощённый анализ на основе диапазона и стабильности
  const range = stats.max - stats.min
  const octaves = Math.log2(stats.max / stats.min)
  
  return {
    brightness: Math.min(100, (stats.max / 700) * 100), // Чем выше макс частота, тем ярче
    stability: Math.min(100, Math.max(0, 100 - (range / 10))), // Чем меньше разброс, тем стабильнее
    power: Math.min(100, stats.validSamples / 3), // Количество сэмплов = сила голоса
    range: Math.min(100, octaves * 50), // Диапазон в октавах
    warmth: Math.min(100, ((400 - stats.min) / 300) * 100), // Низкие ноты = теплота
  }
}

// Медианный фильтр
class MedianFilter {
  constructor(size = 5) {
    this.size = size
    this.buffer = []
  }
  
  push(value) {
    this.buffer.push(value)
    if (this.buffer.length > this.size) this.buffer.shift()
  }
  
  get() {
    if (this.buffer.length === 0) return 0
    const sorted = [...this.buffer].sort((a, b) => a - b)
    const mid = Math.floor(sorted.length / 2)
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
  }
}

// Экспоненциальное сглаживание
class ExponentialSmoothing {
  constructor(alpha = 0.3) {
    this.alpha = alpha
    this.value = 0
    this.initialized = false
  }
  
  update(newValue) {
    if (!this.initialized) {
      this.value = newValue
      this.initialized = true
    } else {
      this.value = this.alpha * newValue + (1 - this.alpha) * this.value
    }
    return this.value
  }
  
  reset() {
    this.value = 0
    this.initialized = false
  }
}

const API_BASE = '/api/v1'

function LiveVoiceAnalyzer() {
  const [isRecording, setIsRecording] = useState(false)
  const [currentFrequency, setCurrentFrequency] = useState(0)
  const [smoothedFrequency, setSmoothedFrequency] = useState(0)
  const [stats, setStats] = useState({ min: Infinity, max: 0, validSamples: 0 })
  const [duration, setDuration] = useState(0)
  const [showResults, setShowResults] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisData, setAnalysisData] = useState(null)
  const [error, setError] = useState(null)
  const [analysisStage, setAnalysisStage] = useState('')
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [isLocked, setIsLocked] = useState(true)
  const [formSubmitted, setFormSubmitted] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: ''
  })

  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const animationFrameRef = useRef(null)
  const startTimeRef = useRef(null)
  const durationIntervalRef = useRef(null)
  
  const medianFilterRef = useRef(new MedianFilter(7))
  const smootherRef = useRef(new ExponentialSmoothing(0.15))
  const frequencyHistoryRef = useRef([])
  useEffect(() => {
    return () => stopRecording()
  }, [])


  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        } 
      })
      mediaStreamRef.current = stream

      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      audioContextRef.current = audioContext

      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 2048
      analyser.smoothingTimeConstant = 0.8
      analyserRef.current = analyser

      const source = audioContext.createMediaStreamSource(stream)
      source.connect(analyser)

      // Записываем аудио для отправки на бэкенд
      audioChunksRef.current = []
      
      // Проверяем поддерживаемые форматы
      let mimeType = 'audio/webm;codecs=opus'
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm'
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/mp4'
          if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = '' // Используем формат по умолчанию
          }
        }
      }
      
      const options = mimeType ? { mimeType } : {}
      const mediaRecorder = new MediaRecorder(stream, options)
      mediaRecorderRef.current = mediaRecorder
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event)
      }
      
      try {
        mediaRecorder.start(100) // Записываем чанки каждые 100мс
      } catch (err) {
        console.error('Failed to start MediaRecorder:', err)
      }

      medianFilterRef.current = new MedianFilter(7)
      smootherRef.current = new ExponentialSmoothing(0.15)
      frequencyHistoryRef.current = []

      setIsRecording(true)
      setStats({ min: Infinity, max: 0, validSamples: 0 })
      setCurrentFrequency(0)
      setSmoothedFrequency(0)
      setError(null)
      setAnalysisData(null)
      startTimeRef.current = Date.now()
      
      durationIntervalRef.current = setInterval(() => {
        if (startTimeRef.current) {
          setDuration(Math.floor((Date.now() - startTimeRef.current) / 1000))
        }
      }, 1000)
      
      detectPitch()
    } catch (err) {
      console.error('Ошибка микрофона:', err)
      alert('Разрешите доступ к микрофону')
    }
  }

  const detectPitch = useCallback(() => {
    if (!analyserRef.current || !audioContextRef.current) return

    const bufferLength = analyserRef.current.fftSize
    const buffer = new Float32Array(bufferLength)
    const sampleRate = audioContextRef.current.sampleRate
    
    let lastUpdate = 0
    const UPDATE_INTERVAL = 50

    const analyze = (timestamp) => {
      if (!analyserRef.current) return
      
      if (timestamp - lastUpdate < UPDATE_INTERVAL) {
        animationFrameRef.current = requestAnimationFrame(analyze)
        return
      }
      lastUpdate = timestamp

      analyserRef.current.getFloatTimeDomainData(buffer)
      const rawFrequency = autoCorrelate(buffer, sampleRate)
      
      if (rawFrequency > 70 && rawFrequency < 1000) {
        const history = frequencyHistoryRef.current
        history.push(rawFrequency)
        if (history.length > 5) history.shift()
        
        medianFilterRef.current.push(rawFrequency)
        const medianFiltered = medianFilterRef.current.get()
        const smoothed = smootherRef.current.update(medianFiltered)
        
        // Обновляем статистику
        setStats(prev => {
          const newValidSamples = prev.validSamples + 1
          
          // Игнорируем первые 2 валидных сэмпла чтобы избежать ложных высоких значений
          // Также проверяем что частота разумная (не выше 600 Hz для вокала)
          const isValidSample = newValidSamples >= 2 && smoothed < 600 && smoothed > 70
          
          if (isValidSample) {
            // Показываем частоту только если она валидная
            setCurrentFrequency(rawFrequency)
            setSmoothedFrequency(smoothed)
            
            return {
              min: Math.min(prev.min === Infinity ? smoothed : prev.min, smoothed),
              max: Math.max(prev.max === 0 ? smoothed : prev.max, smoothed),
              validSamples: newValidSamples,
            }
          } else {
            // Считаем сэмплы но не показываем частоту пока не накопится достаточно данных
            return {
              ...prev,
              validSamples: newValidSamples,
            }
          }
        })
      }

      animationFrameRef.current = requestAnimationFrame(analyze)
    }

    animationFrameRef.current = requestAnimationFrame(analyze)
  }, [])

  const autoCorrelate = (buffer, sampleRate) => {
    const size = buffer.length
    const halfSize = Math.floor(size / 2)
    
    // Вычисляем RMS (Root Mean Square) для определения уровня сигнала
    let rms = 0
    for (let i = 0; i < size; i += 4) {
      rms += buffer[i] * buffer[i]
    }
    rms = Math.sqrt(rms / (size / 4))
    
    // Увеличиваем порог для тишины и добавляем проверку на стабильность
    // 0.01 вместо 0.005 - более строгая фильтрация шума
    if (rms < 0.01) return -1
    
    // Дополнительная проверка: если сигнал слишком слабый или нестабильный
    // Проверяем разброс значений (variance)
    let variance = 0
    let mean = 0
    for (let i = 0; i < size; i += 4) {
      mean += buffer[i]
    }
    mean /= (size / 4)
    for (let i = 0; i < size; i += 4) {
      variance += (buffer[i] - mean) ** 2
    }
    variance /= (size / 4)
    
    // Если сигнал слишком стабильный (низкая variance), это скорее всего шум, а не голос
    if (variance < 0.0001) return -1

    let bestOffset = -1
    let bestCorrelation = 0.8  // Увеличиваем порог с 0.75 до 0.8 для более строгой фильтрации
    let lastCorrelation = 1

    const minPeriod = Math.floor(sampleRate / 1000)  // Минимум 1kHz
    const maxPeriod = Math.floor(sampleRate / 70)    // Максимум 70Hz

    for (let offset = minPeriod; offset < Math.min(maxPeriod, halfSize); offset++) {
      let correlation = 0
      for (let i = 0; i < halfSize; i += 2) {
        correlation += Math.abs(buffer[i] - buffer[i + offset])
      }
      correlation = 1 - (correlation / halfSize * 2)

      // Более строгая проверка: нужна не только высокая корреляция, но и стабильность
      if (correlation > bestCorrelation && correlation > lastCorrelation) {
        bestCorrelation = correlation
        bestOffset = offset
      }
      lastCorrelation = correlation
    }

    // Дополнительная проверка: если корреляция слишком низкая, это скорее всего шум
    if (bestCorrelation < 0.8) return -1

    return bestOffset > 0 ? sampleRate / bestOffset : -1
  }

  const stopRecording = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current)
      durationIntervalRef.current = null
    }

    // Останавливаем запись аудио
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop())
      mediaStreamRef.current = null
    }

    if (audioContextRef.current?.state !== 'closed') {
      audioContextRef.current?.close()
      audioContextRef.current = null
    }

    analyserRef.current = null
    setIsRecording(false)
  }, [])

  const handleFinish = async () => {
    // Дополнительная защита (кнопка уже disabled до 15 сек)
    if (duration < 15) {
      return
    }

    stopRecording()

    // Ждем завершения записи аудио
    if (mediaRecorderRef.current) {
      await new Promise((resolve) => {
        mediaRecorderRef.current.onstop = resolve
        if (mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop()
        } else {
          resolve()
        }
      })
    }

    // Отправляем на анализ
    await sendForAnalysis()
  }

  const sendForAnalysis = async () => {
    if (audioChunksRef.current.length === 0) {
      setError('Не удалось записать аудио. Убедись, что микрофон работает и разрешен доступ.')
      setShowResults(true)
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setAnalysisStage('Подготовка записи...')
    setAnalysisProgress(10)

    try {
      // Определяем тип файла
      const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm'
      const extension = mimeType.includes('mp4') ? 'm4a' : mimeType.includes('webm') ? 'webm' : 'wav'
      
      // Создаем Blob из записанных чанков
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
      
      // Проверяем размер
      if (audioBlob.size === 0) {
        throw new Error('Записанный файл пуст')
      }
      
      setAnalysisStage('Загрузка аудио...')
      setAnalysisProgress(20)
      
      const formData = new FormData()
      formData.append('file', audioBlob, `recording.${extension}`)
      
      // Загружаем аудио
      const uploadRes = await fetch(`${API_BASE}/upload-audio`, {
        method: 'POST',
        body: formData,
      })
      
      if (!uploadRes.ok) {
        const err = await uploadRes.json()
        throw new Error(err.detail || 'Ошибка загрузки аудио')
      }
      
      const uploadData = await uploadRes.json()
      
      setAnalysisStage('Анализ тона голоса...')
      setAnalysisProgress(40)
      
      // Запускаем анализ
      const analysisRes = await fetch(
        `${API_BASE}/analyze-voice?session_id=${uploadData.session_id}`,
        { method: 'POST' }
      )
      
      setAnalysisStage('Извлечение тембра...')
      setAnalysisProgress(60)
      
      if (!analysisRes.ok) {
        const err = await analysisRes.json()
        throw new Error(err.detail || 'Ошибка анализа')
      }
      
      setAnalysisStage('Поиск похожих артистов...')
      setAnalysisProgress(80)
      
      const result = await analysisRes.json()
      
      setAnalysisStage('Готово!')
      setAnalysisProgress(100)
      
      // Небольшая задержка перед показом результатов
      await new Promise(resolve => setTimeout(resolve, 500))
      
      setAnalysisData(result)
      setShowResults(true)
      
    } catch (err) {
      console.error('Ошибка анализа:', err)
      setError(err.message)
      setShowResults(true)
    } finally {
      setIsAnalyzing(false)
      setAnalysisStage('')
      setAnalysisProgress(0)
    }
  }

  const reset = () => {
    setShowResults(false)
    setCurrentFrequency(0)
    setSmoothedFrequency(0)
    setStats({ min: Infinity, max: 0, validSamples: 0 })
    setDuration(0)
    setAnalysisData(null)
    setError(null)
    setIsAnalyzing(false)
    startTimeRef.current = null
    frequencyHistoryRef.current = []
    audioChunksRef.current = []
  }

  const displayFrequency = smoothedFrequency > 0 ? smoothedFrequency : currentFrequency
  const currentNote = useMemo(() => hzToNote(displayFrequency), [displayFrequency])
  const minNote = useMemo(() => hzToNote(stats.min), [stats.min])
  const maxNote = useMemo(() => hzToNote(stats.max), [stats.max])
  const voiceType = useMemo(() => detectVoiceType(stats.min, stats.max), [stats.min, stats.max])
  const timbre = useMemo(() => analyzeTimbr(stats), [stats])
  
  const needleRotation = useMemo(() => {
    if (displayFrequency <= 0) return -90
    const minLog = Math.log2(70)
    const maxLog = Math.log2(1000)
    const currentLog = Math.log2(Math.max(70, Math.min(1000, displayFrequency)))
    return ((currentLog - minLog) / (maxLog - minLog)) * 180 - 90
  }, [displayFrequency])

  const octaveRange = useMemo(() => {
    if (stats.min === Infinity || stats.max === 0 || stats.validSamples < 10) return 0
    return Math.log2(stats.max / stats.min)
  }, [stats])

  // Пояснения для тембра
  const timbreExplanations = {
    brightness: { 
      label: 'Яркость голоса', 
      low: 'Мягкий, бархатный тембр', 
      mid: 'Сбалансированный, приятный тембр',
      high: 'Звонкий, пронзительный голос' 
    },
    stability: { 
      label: 'Стабильность', 
      low: 'Голос "плавает", требует работы', 
      mid: 'Хорошая стабильность',
      high: 'Отличный контроль голоса!' 
    },
    power: { 
      label: 'Сила подачи', 
      low: 'Тихое пение, больше уверенности!', 
      mid: 'Хорошая громкость',
      high: 'Мощный, уверенный голос!' 
    },
    range: { 
      label: 'Диапазон', 
      low: 'Узкий диапазон (до 1 октавы)', 
      mid: 'Средний диапазон (1-2 октавы)',
      high: 'Широкий диапазон (2+ октавы)' 
    },
    warmth: { 
      label: 'Теплота', 
      low: 'Холодный, высокий тембр', 
      mid: 'Нейтральный тембр',
      high: 'Тёплый, глубокий тембр' 
    },
  }

  const getTimbreLevel = (value) => {
    if (value < 33) return 'low'
    if (value < 66) return 'mid'
    return 'high'
  }

  return (
    <div className="max-w-2xl mx-auto">
      <AnimatePresence mode="wait">
        {isAnalyzing ? (
          <motion.div
            key="analyzing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="max-w-md mx-auto py-12"
          >
            {/* Анимированная иконка */}
            <div className="relative w-20 h-20 mx-auto mb-6">
              <motion.div
                animate={{
                  scale: [1, 1.2, 1],
                  rotate: [0, 180, 360],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
                className="absolute inset-0 rounded-full bg-gradient-to-br from-primary to-accent opacity-20"
              />
              <motion.div
                animate={{
                  scale: [1.2, 1, 1.2],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
                className="absolute inset-2 rounded-full bg-gradient-to-br from-primary to-accent opacity-40"
              />
              <div className="absolute inset-0 flex items-center justify-center">
                <Activity className="w-10 h-10 text-primary" />
              </div>
            </div>
            
            {/* Текущий этап */}
            <motion.p
              key={analysisStage}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-lg font-medium text-slate-800 text-center mb-2"
            >
              {analysisStage || 'Загрузка...'}
            </motion.p>
            
            {/* Прогресс бар */}
            <div className="w-full bg-slate-100 rounded-full h-2 mb-2 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${analysisProgress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="h-full bg-gradient-to-r from-primary to-accent rounded-full"
              />
            </div>
            
            {/* Процент */}
            <p className="text-sm text-slate-500 text-center mb-6">
              {analysisProgress}%
            </p>
            
            {/* Список этапов */}
            <div className="space-y-2">
              {[
                { label: 'Подготовка записи', threshold: 10 },
                { label: 'Загрузка аудио', threshold: 20 },
                { label: 'Анализ тона голоса', threshold: 40 },
                { label: 'Извлечение тембра', threshold: 60 },
                { label: 'Поиск похожих артистов', threshold: 80 },
                { label: 'Подбор песен', threshold: 90 },
              ].map((stage, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`flex items-center gap-2 text-sm ${
                    analysisProgress >= stage.threshold ? 'text-primary' : 'text-slate-400'
                  }`}
                >
                  {analysisProgress >= stage.threshold ? (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="w-5 h-5 rounded-full bg-primary flex items-center justify-center"
                    >
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </motion.div>
                  ) : (
                    <div className="w-5 h-5 rounded-full border-2 border-slate-300" />
                  )}
                  <span>{stage.label}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        ) : !showResults ? (
          <motion.div
            key="recording"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="text-center mb-6">
              <h2 className="font-display font-bold text-2xl text-slate-800 mb-2">
                Live анализ голоса
              </h2>
              {!isRecording && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-left max-w-md mx-auto"
                >
                  <div className="flex gap-3">
                    <Info className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-slate-700 text-sm mb-2">
                        <strong>Как получить точный результат:</strong>
                      </p>
                      <ul className="text-slate-600 text-sm space-y-1">
                        <li>🎤 Напой <strong>минимум 15 секунд</strong> любимую песню</li>
                        <li>🎵 Выбери ту, которая хорошо у тебя получается</li>
                        <li>📢 Пой в полный голос, не стесняйся!</li>
                        <li>🔇 Найди тихое место без шума</li>
                      </ul>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Спидометр и шкала */}
            <div className="flex gap-4 items-center justify-center mb-4">
              {isRecording && (
                <motion.div 
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex flex-col justify-between h-48 py-2"
                >
                  {[1000, 800, 600, 400, 200, 100, 70].map((hz) => {
                    const isNear = displayFrequency > 0 && Math.abs(displayFrequency - hz) < 50
                    return (
                      <div key={hz} className="flex items-center gap-2">
                        <div className={`text-xs transition-all ${
                          isNear ? 'text-primary font-semibold text-sm' : 'text-slate-400'
                        }`}>
                          {hz}
                        </div>
                        <div className={`h-px transition-all ${
                          isNear ? 'w-3 bg-primary' : 'w-2 bg-slate-300'
                        }`} />
                      </div>
                    )
                  })}
                </motion.div>
              )}
              
              <div className="relative w-full max-w-xs">
                <svg viewBox="-10 -10 220 150" className="w-full">
                  <defs>
                    <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#72AEF7" />
                      <stop offset="100%" stopColor="#5A9DE6" />
                    </linearGradient>
                  </defs>
                  
                  <path
                    d="M 20 100 A 80 80 0 0 1 180 100"
                    fill="none"
                    stroke="#e2e8f0"
                    strokeWidth="10"
                    strokeLinecap="round"
                  />
                  
                  {isRecording && displayFrequency > 0 && (
                    <motion.path
                      d="M 20 100 A 80 80 0 0 1 180 100"
                      fill="none"
                      stroke="url(#gaugeGrad)"
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={`${(needleRotation + 90) * 1.4} 300`}
                      transition={{ duration: 0.2, ease: "easeOut" }}
                    />
                  )}
                  
                  <g style={{
                    transformBox: 'view-box',
                    transformOrigin: '50% 73.33%',
                    transition: 'transform 0.4s ease-out',
                    transform: `rotate(${needleRotation}deg)`,
                  }}>
                    <line
                      x1="100" y1="100" x2="100" y2="35"
                      stroke={isRecording ? '#72AEF7' : '#94a3b8'}
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                    <circle cx="100" cy="100" r="6" fill={isRecording ? '#72AEF7' : '#94a3b8'} />
                  </g>
                  
                  {[
                    { label: '70', freq: 70 },
                    { label: 'Ре3', freq: 130 },
                    { label: 'До4', freq: 261 },
                    { label: 'До5', freq: 523 },
                    { label: '1к', freq: 1000 }
                  ].map(({ label }, i) => {
                    const angle = (i / 4) * 180 - 90
                    const x = 100 + Math.cos((angle * Math.PI) / 180) * 95
                    const y = 100 + Math.sin((angle * Math.PI) / 180) * 95
                    return (
                      <text key={label} x={x} y={y} textAnchor="middle" fontSize="9" fill="#94a3b8">
                        {label}
                      </text>
                    )
                  })}
                </svg>

                <div className="absolute inset-0 flex flex-col items-center justify-center pt-4">
                  <AnimatePresence mode="wait">
                    {displayFrequency > 0 ? (
                      <motion.div
                        key="note"
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.8, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="text-center"
                      >
                        <div className="font-display font-bold text-4xl text-primary">
                          {currentNote.noteRu}
                          <span className="text-xl text-primary/70">{currentNote.octave}</span>
                        </div>
                        <motion.div 
                          className="text-primary text-lg font-semibold"
                          animate={{ opacity: [0.6, 1, 0.6] }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        >
                          {Math.round(displayFrequency)} Hz
                        </motion.div>
                      </motion.div>
                    ) : (
                      <motion.div
                        key="waiting"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="text-slate-400 text-sm text-center"
                      >
                        {isRecording ? 'Жду голос...' : '—'}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>


            {/* Кнопка */}
            <div className="flex justify-center">
              {!isRecording ? (
                <button
                  onClick={() => {
                      startRecording()
                      ymReachGoal('nachat_pet');
                      }}
                  className="flex items-center gap-3 px-8 py-4 rounded-[40px] btn-primary shadow-lg shadow-primary/20"
                >
                  <Mic className="w-5 h-5" />
                  <span className="font-semibold">Начать петь</span>
                </button>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <button
                    onClick={() => {
                        handleFinish()
                        ymReachGoal('zakonchit_pet');
                        }}
                    disabled={duration < 15}
                    className={`flex items-center gap-3 px-8 py-4 rounded-[40px] transition-all ${
                      duration >= 15
                        ? 'bg-red-500 text-white hover:bg-red-600 pulse-record cursor-pointer'
                        : 'bg-slate-300 text-slate-500 cursor-not-allowed'
                    }`}
                  >
                    <MicOff className="w-5 h-5" />
                    <span className="font-semibold">
                      {duration >= 15 ? `Закончить (${duration}с)` : `Записываю... (${duration}с / минимум 15с)`}
                    </span>
                  </button>
                  {duration < 15 && (
                    <motion.p
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-xs text-slate-600 font-medium"
                    >
                      Ещё {15 - duration}с до возможности завершить
                    </motion.p>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-3xl mx-auto"
          >
            {/* Hero - тип голоса */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gradient-to-br from-primary to-accent rounded-2xl p-6 mb-6 text-white"
            >
              <div className="flex flex-col md:flex-row items-center gap-5">
                <div className="w-16 h-16 rounded-xl bg-white/20 flex items-center justify-center">
                  <Mic2 className="w-8 h-8" />
                </div>
                <div className="text-center md:text-left">
                  <p className="text-white/70 text-sm">Твой тип голоса</p>
                  <h2 className="font-display font-bold text-3xl mb-1">{voiceType.name}</h2>
                  <p className="text-white/80 text-sm">{voiceType.desc}</p>
                  {stats.validSamples > 10 && (
                    <p className="text-white/90 mt-1">
                      <span className="font-semibold">{minNote.fullRu}</span>
                      {' — '}
                      <span className="font-semibold">{maxNote.fullRu}</span>
                      <span className="text-white/60 ml-2">({octaveRange.toFixed(1)} октав)</span>
                    </p>
                  )}
                </div>
                <div className="md:ml-auto flex gap-4">
                  {[
                    { label: 'Мин', value: Math.round(stats.min), unit: 'Hz' },
                    { label: 'Макс', value: Math.round(stats.max), unit: 'Hz' },
                    { label: 'Время', value: duration, unit: 'с' },
                  ].map(item => (
                    <div key={item.label} className="px-4 py-2 rounded-lg bg-white/10 text-center">
                      <div className="font-mono text-lg">{item.value}</div>
                      <div className="text-white/60 text-xs">{item.label} {item.unit}</div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>


            {/* Спектрограмма */}
            {isRecording && analyserRef.current && (
              <div className="mb-4">
                <Spectrogram analyser={analyserRef.current} isActive={isRecording} />
              </div>
            )}

            {/* Статистика */}
            {isRecording && (
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="bg-white rounded-xl p-3 border border-slate-100 text-center">
                  <div className="text-slate-400 text-xs mb-1">Мин</div>
                  <div className="font-semibold text-slate-700">
                    {stats.min !== Infinity && stats.validSamples > 5 ? minNote.fullRu : '—'}
                  </div>
                </div>
                <div className="bg-white rounded-xl p-3 border border-slate-100 text-center">
                  <div className="text-slate-400 text-xs mb-1">Время</div>
                  <div className="font-mono text-slate-700">{duration}с</div>
                </div>
                <div className="bg-white rounded-xl p-3 border border-slate-100 text-center">
                  <div className="text-slate-400 text-xs mb-1">Макс</div>
                  <div className="font-semibold text-slate-700">
                    {stats.max > 0 && stats.validSamples > 5 ? maxNote.fullRu : '—'}
                  </div>
                </div>
              </div>
            )}

            {/* Диапазон визуализация */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-white rounded-2xl p-5 border border-slate-100 mb-6"
            >
              <div className="flex items-center gap-2 mb-3">
                <Activity className="w-4 h-4 text-primary" />
                <h3 className="font-semibold text-slate-800">Твой вокальный диапазон</h3>
              </div>
              <div className="relative h-12 bg-slate-100 rounded-lg">
                {/* Шкала - черные ноты */}
                <div className="absolute inset-0 flex items-center justify-between px-4 text-xs text-slate-800 font-medium pointer-events-none">
                  <span>До2</span>
                  <span>До3</span>
                  <span>До4</span>
                  <span>До5</span>
                  <span>До6</span>
                </div>
                {/* Твой диапазон с белыми нотами */}
                {stats.validSamples > 10 && (
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${Math.min(100, octaveRange * 25)}%`,
                      left: `${Math.max(0, ((Math.log2(stats.min) - Math.log2(65)) / 4) * 100)}%`
                    }}
                    transition={{ duration: 0.8 }}
                    className="absolute h-full bg-gradient-to-r from-primary to-accent opacity-80 rounded overflow-hidden"
                  >
                    {/* Белые ноты поверх синего */}
                    <div className="absolute h-full flex items-center justify-between px-4 text-xs text-white font-medium pointer-events-none"
                         style={{
                           width: `${100 / (Math.min(100, octaveRange * 25) / 100)}%`,
                           left: `-${(Math.max(0, ((Math.log2(stats.min) - Math.log2(65)) / 4) * 100) / (Math.min(100, octaveRange * 25) / 100))}%`
                         }}>
                      <span>До2</span>
                      <span>До3</span>
                      <span>До4</span>
                      <span>До5</span>
                      <span>До6</span>
                    </div>
                  </motion.div>
                )}
              </div>
              <div className="flex justify-between mt-2 text-sm">
                <span className="text-slate-600">
                  Нижняя нота: <strong className="text-primary">{minNote.fullRu}</strong> ({Math.round(stats.min)} Hz)
                </span>
                <span className="text-slate-600">
                  Верхняя нота: <strong className="text-primary">{maxNote.fullRu}</strong> ({Math.round(stats.max)} Hz)
                </span>
              </div>
            </motion.div>

            {/* Тембр с пояснениями */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-2xl p-5 border border-slate-100 mb-6"
            >
              <div className="flex items-center gap-2 mb-4">
                <Gauge className="w-4 h-4 text-accent" />
                <h3 className="font-semibold text-slate-800">Характеристики голоса</h3>
              </div>
              <div className="space-y-4">
                {Object.entries(timbre).map(([key, value], i) => {
                  const explanation = timbreExplanations[key]
                  const level = getTimbreLevel(value)
                  return (
                    <motion.div
                      key={key}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                    >
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-700 font-medium">{explanation.label}</span>
                        <span className="font-mono text-primary">{Math.round(value)}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 overflow-hidden mb-1">
                        <motion.div
                          className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                          initial={{ width: 0 }}
                          animate={{ width: `${value}%` }}
                          transition={{ duration: 0.5, delay: 0.1 + i * 0.1 }}
                        />
                      </div>
                      <p className="text-xs text-slate-500">{explanation[level]}</p>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>

            {/* Ошибка */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-50 border border-red-200 rounded-2xl p-5 mb-6"
              >
                <div className="flex items-center gap-2 text-red-700">
                  <AlertCircle className="w-5 h-5" />
                  <p className="font-medium">Ошибка анализа: {error}</p>
                </div>
              </motion.div>
            )}

            {/* Форма разблокировки */}
            {isLocked && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white rounded-2xl p-6 border border-slate-100 mb-6"
              >
                <form onSubmit={async (e) => {
                  e.preventDefault();
                  await sendToTelegram(formData);
                  setIsLocked(false);
                  setFormSubmitted(true);
                }} className="w-full max-w-md mx-auto">
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                      <Lock className="w-8 h-8 text-primary" />
                    </div>
                    <h3 className="font-semibold text-slate-800 text-lg mb-2">Открыть рекомендации</h3>
                    <p className="text-sm text-slate-500">Заполни форму для доступа к подборке похожих артистов и песен</p>
                  </div>

                  <div className="space-y-3">
                    <input
                      type="text"
                      placeholder="Имя"
                      required
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-2xl border-2 border-slate-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all text-sm bg-white"
                    />
                    <input
                      type="tel"
                      placeholder="Телефон"
                      required
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="w-full px-4 py-3 rounded-2xl border-2 border-slate-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all text-sm bg-white"
                    />
                    <input
                      type="email"
                      placeholder="Email"
                      required
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-4 py-3 rounded-2xl border-2 border-slate-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all text-sm bg-white"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full mt-4 px-4 py-3 rounded-[40px] bg-primary text-white font-medium text-sm hover:bg-primary/90 transition-colors shadow-md shadow-primary/20"
                    onClick={() => {
                        ymReachGoal('otpravka_formi_analiz');
                        }}
                  >
                    Отправить
                  </button>
                  <p className="text-xs text-slate-500 text-center mt-3">
                    Нажимая на кнопку «Отправить», я даю согласие на обработку{' '}
                    <a href="https://simplyonline.ru/policy" target="_blank" className="text-primary hover:underline">Персональных данных</a>
                    {' '}и принимаю условия{' '}
                    <a href="https://simplyonline.ru/useragreement" target="_blank" className="text-primary hover:underline">Пользовательского соглашения</a>
                  </p>
                </form>
              </motion.div>
            )}

            {/* Блок консультации после отправки формы */}
            {!isLocked && formSubmitted && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-white rounded-2xl p-6 border border-slate-100 mb-6"
              >
                <div className="w-full max-w-md mx-auto">
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                      <User className="w-8 h-8 text-primary" />
                    </div>
                    <h3 className="font-semibold text-slate-800 text-lg mb-2">
                      Запишитесь на онлайн-консультацию со скидкой 55%
                    </h3>
                    <p className="text-sm text-slate-500">
                      Анализ от ИИ помогает увидеть общую картину. Но по-настоящему профессионально оценить ваш голос, дать точные рекомендации и персональные советы может только опытный преподаватель
                    </p>
                  </div>

                  <a
                    href="https://app.simplyonline.ru/teachers"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full px-4 py-3 rounded-[40px] bg-primary text-white font-medium text-sm hover:bg-primary/90 transition-colors shadow-md shadow-primary/20 text-center"
                    onClick={() => setFormSubmitted(false)}
                  >
                    Записаться
                  </a>
                </div>
              </motion.div>
            )}

            {/* Похожие артисты из API */}
            {analysisData?.top_similar_artists && Array.isArray(analysisData.top_similar_artists) && analysisData.top_similar_artists.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-white rounded-2xl p-5 border border-slate-100 mb-6"
              >
                <div className="flex items-center gap-2 mb-4">
                  <User className="w-4 h-4 text-primary" />
                  <h3 className="font-semibold text-slate-800">Похожие артисты</h3>
                </div>
                <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 ${isLocked ? 'blur-sm pointer-events-none' : ''}`}>
                  {analysisData.top_similar_artists.map((artist, i) => (
                    artist ? <ArtistCard key={artist.artist_id || i} artist={artist} rank={i + 1} /> : null
                  ))}
                </div>
              </motion.div>
            )}

            {/* Рекомендованные песни из API */}
            {analysisData?.recommended_songs && Array.isArray(analysisData.recommended_songs) && analysisData.recommended_songs.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="bg-white rounded-2xl p-5 border border-slate-100 mb-6"
              >
                <div className="flex items-center gap-2 mb-4">
                  <Music className="w-4 h-4 text-primary" />
                  <h3 className="font-semibold text-slate-800">Рекомендованные песни</h3>
                </div>
                <div className={`space-y-3 ${isLocked ? 'blur-sm pointer-events-none' : ''}`}>
                  {analysisData.recommended_songs.map((song, i) => (
                    song ? <SongCard key={song.song_id || i} song={song} isLocked={isLocked} /> : null
                  ))}
                </div>
              </motion.div>
            )}

            {/* Рекомендации (если нет данных от API) */}
            {(!analysisData || !analysisData.top_similar_artists) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-blue-50 border border-blue-200 rounded-2xl p-5 mb-6"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Music className="w-4 h-4 text-primary" />
                  <h3 className="font-semibold text-slate-800">Что дальше?</h3>
                </div>
                <p className="text-slate-600 text-sm mb-3">
                  Твой голос типа <strong>{voiceType.name}</strong> отлично подойдёт для:
                </p>
                <div className="flex flex-wrap gap-2">
                  {voiceType.type === 'bass' && ['Рок-баллады', 'Джаз', 'Блюз', 'Классика'].map(g => (
                    <span key={g} className="px-3 py-1 bg-white rounded-full text-sm text-slate-600">{g}</span>
                  ))}
                  {voiceType.type === 'baritone' && ['Поп', 'Рок', 'R&B', 'Соул'].map(g => (
                    <span key={g} className="px-3 py-1 bg-white rounded-full text-sm text-slate-600">{g}</span>
                  ))}
                  {voiceType.type === 'tenor' && ['Поп', 'Рок', 'Фолк', 'Мюзиклы'].map(g => (
                    <span key={g} className="px-3 py-1 bg-white rounded-full text-sm text-slate-600">{g}</span>
                  ))}
                  {voiceType.type === 'alto' && ['Джаз', 'Соул', 'R&B', 'Фолк'].map(g => (
                    <span key={g} className="px-3 py-1 bg-white rounded-full text-sm text-slate-600">{g}</span>
                  ))}
                  {voiceType.type === 'mezzo-soprano' && ['Поп', 'Мюзиклы', 'R&B', 'Эстрада'].map(g => (
                    <span key={g} className="px-3 py-1 bg-white rounded-full text-sm text-slate-600">{g}</span>
                  ))}
                  {voiceType.type === 'soprano' && ['Поп', 'Классика', 'Мюзиклы', 'Опера'].map(g => (
                    <span key={g} className="px-3 py-1 bg-white rounded-full text-sm text-slate-600">{g}</span>
                  ))}
                </div>
              </motion.div>
            )}

            <div className="flex justify-center">
              <button
                onClick={reset}
                className="flex items-center gap-2 px-6 py-3 rounded-[40px] btn-primary"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Попробовать ещё раз</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default LiveVoiceAnalyzer
