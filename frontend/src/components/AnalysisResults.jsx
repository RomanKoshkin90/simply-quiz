import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Music, User, Activity, Gauge, Mic2, Lock } from 'lucide-react'
import VocalRangeChart from './VocalRangeChart'
import ArtistCard from './ArtistCard'
import SongCard from './SongCard'
import TimbreRadar from './TimbreRadar'

// Русские названия нот
const NOTE_NAMES_RU = {
  'C': 'До', 'C#': 'До#', 'D': 'Ре', 'D#': 'Ре#',
  'E': 'Ми', 'F': 'Фа', 'F#': 'Фа#', 'G': 'Соль',
  'G#': 'Соль#', 'A': 'Ля', 'A#': 'Ля#', 'B': 'Си'
}

// Конвертация ноты в русский формат
const toRussianNote = (note) => {
  if (!note || note === '—') return '—'
  // Формат: C4, C#3, D5 и т.д.
  const match = note.match(/^([A-G]#?)(\d)$/)
  if (!match) return note
  const [, noteName, octave] = match
  const ruNote = NOTE_NAMES_RU[noteName] || noteName
  return `${ruNote}${octave}`
}

const voiceTypeNames = {
  'bass': 'Бас', 'baritone': 'Баритон', 'tenor': 'Тенор',
  'alto': 'Альт', 'mezzo-soprano': 'Меццо-сопрано', 'soprano': 'Сопрано',
}

const voiceTypeDescriptions = {
  'bass': 'Самый низкий мужской голос — глубокий и мощный',
  'baritone': 'Средний мужской голос — универсальный и выразительный',
  'tenor': 'Высокий мужской голос — яркий и эмоциональный',
  'alto': 'Низкий женский голос — тёплый и насыщенный',
  'mezzo-soprano': 'Средний женский голос — гибкий и разнообразный',
  'soprano': 'Высокий женский голос — лёгкий и полётный',
}

function AnalysisResults({ data }) {
  const { pitch_analysis, timbre_features, top_similar_artists, recommended_songs } = data
  const voiceTypeName = voiceTypeNames[pitch_analysis.detected_voice_type] || pitch_analysis.detected_voice_type
  const voiceTypeDesc = voiceTypeDescriptions[pitch_analysis.detected_voice_type] || ''

  const minNoteRu = toRussianNote(pitch_analysis.min_pitch_note)
  const maxNoteRu = toRussianNote(pitch_analysis.max_pitch_note)

  const [isLocked, setIsLocked] = useState(true)
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: ''
  })

  // Отправка в Telegram
  const sendToTelegram = async (data) => {
    const TELEGRAM_BOT_TOKEN = '8408102586:AAEP9p5SDgLxaIol02B0qkBIESFZbdYXJsM'
    const TELEGRAM_CHAT_ID = '-5281969218'

    const message = `🎵 Новая заявка в квизе\n\n👤 Имя: ${data.name}\n📱 Телефон: ${data.phone}\n📧 Email: ${data.email}`

    try {
      const response = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: TELEGRAM_CHAT_ID,
          text: message,
          parse_mode: 'HTML'
        })
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      return true
    } catch (error) {
      console.error('Error sending to Telegram:', error)
      return false
    }
  }

  // Автоматическая разблокировка при заполнении всех полей
  useEffect(() => {
    const isFormValid = formData.name.trim() !== '' &&
                       formData.phone.trim() !== '' &&
                       formData.email.trim() !== '' &&
                       formData.email.includes('@')

    if (isFormValid && isLocked) {
      const timer = setTimeout(() => {
        console.log('Songs unlocked:', formData)
        setIsLocked(false)
      }, 500)

      return () => clearTimeout(timer)
    }
  }, [formData, isLocked])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="max-w-5xl mx-auto"
    >
      {/* Hero */}
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
            <h2 className="font-display font-bold text-3xl mb-1">{voiceTypeName}</h2>
            <p className="text-white/80 text-sm mb-1">{voiceTypeDesc}</p>
            <p className="text-white/90">
              <span className="font-semibold">{minNoteRu}</span>
              {' — '}
              <span className="font-semibold">{maxNoteRu}</span>
              <span className="text-white/60 ml-2">({pitch_analysis.octave_range.toFixed(1)} октав)</span>
            </p>
          </div>
          <div className="md:ml-auto flex gap-4">
            {[
              { label: 'Мин', value: Math.round(pitch_analysis.min_pitch_hz) },
              { label: 'Медиана', value: Math.round(pitch_analysis.median_pitch_hz) },
              { label: 'Макс', value: Math.round(pitch_analysis.max_pitch_hz) },
            ].map(item => (
              <div key={item.label} className="px-4 py-2 rounded-lg bg-white/10 text-center">
                <div className="font-mono text-lg">{item.value}</div>
                <div className="text-white/60 text-xs">{item.label} Hz</div>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Диапазон */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white rounded-2xl p-5 border border-slate-100 mb-6"
      >
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-slate-800">Вокальный диапазон</h3>
        </div>
        <VocalRangeChart 
          minHz={pitch_analysis.min_pitch_hz}
          maxHz={pitch_analysis.max_pitch_hz}
          medianHz={pitch_analysis.median_pitch_hz}
          voiceType={pitch_analysis.detected_voice_type}
        />
        <div className="flex justify-between mt-3 text-sm text-slate-600">
          <span>Нижняя нота: <strong className="text-primary">{minNoteRu}</strong></span>
          <span>Верхняя нота: <strong className="text-primary">{maxNoteRu}</strong></span>
        </div>
      </motion.div>

      {/* Тембр + Артисты */}
      <div className="grid md:grid-cols-2 gap-5 mb-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-2xl p-5 border border-slate-100"
        >
          <div className="flex items-center gap-2 mb-3">
            <Gauge className="w-4 h-4 text-accent" />
            <h3 className="font-semibold text-slate-800">Характеристики тембра</h3>
          </div>
          <TimbreRadar features={timbre_features} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl p-5 border border-slate-100"
        >
          <div className="flex items-center gap-2 mb-3">
            <User className="w-4 h-4 text-primary" />
            <h3 className="font-semibold text-slate-800">Похожие артисты</h3>
          </div>
          <div className={`space-y-2 ${isLocked ? 'blur-sm pointer-events-none' : ''}`}>
            {top_similar_artists.length > 0 ? (
              top_similar_artists.map((artist, i) => (
                <ArtistCard key={artist.artist_id} artist={artist} rank={i + 1} />
              ))
            ) : (
              <div className="text-center py-6">
                <p className="text-slate-400 text-sm mb-2">Пока нет данных для сравнения</p>
                <p className="text-slate-300 text-xs">База артистов формируется</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Песни */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-white rounded-2xl p-5 border border-slate-100 relative"
      >
        <div className="flex items-center gap-2 mb-3">
          <Music className="w-4 h-4 text-accent" />
          <h3 className="font-semibold text-slate-800">Песни, которые тебе подойдут</h3>
        </div>

        {recommended_songs.length > 0 ? (
          <div className="relative">
            {/* Форма разблокировки */}
            <AnimatePresence>
              {isLocked && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 z-10 flex items-center justify-center bg-white/40 backdrop-blur-md rounded-xl p-6"
                >
                  <form onSubmit={async (e) => {
                    e.preventDefault();
                    await sendToTelegram(formData);
                    setIsLocked(false);
                  }} className="w-full max-w-md">
                    <div className="text-center mb-6">
                      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                        <Lock className="w-8 h-8 text-primary" />
                      </div>
                      <h3 className="font-semibold text-slate-800 text-lg mb-2">Открыть рекомендации</h3>
                      <p className="text-sm text-slate-500">Заполни форму для доступа к подборке песен</p>
                    </div>

                    <div className="space-y-3">
                      <input
                        type="text"
                        placeholder="Имя"
                        required
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all text-sm bg-white"
                      />
                      <input
                        type="tel"
                        placeholder="Телефон"
                        required
                        value={formData.phone}
                        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all text-sm bg-white"
                      />
                      <input
                        type="email"
                        placeholder="Email"
                        required
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all text-sm bg-white"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full mt-4 px-4 py-3 rounded-lg bg-primary text-white font-medium text-sm hover:bg-primary/90 transition-colors shadow-md shadow-primary/20"
                    >
                      Отправить
                    </button>
                  </form>
                </motion.div>
              )}
            </AnimatePresence>

            <div className={`grid sm:grid-cols-2 lg:grid-cols-3 gap-3 ${isLocked ? 'blur-sm pointer-events-none' : ''}`}>
              {recommended_songs.slice(0, 6).map(song => (
                <SongCard key={song.song_id} song={song} isLocked={isLocked} />
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-6">
            <p className="text-slate-400 text-sm mb-2">Песни появятся скоро!</p>
            <p className="text-slate-300 text-xs">Мы подберём идеальный репертуар для твоего голоса</p>
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}

export default AnalysisResults
