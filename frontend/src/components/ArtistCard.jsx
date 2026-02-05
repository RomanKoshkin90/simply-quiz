import { motion } from 'framer-motion'

const medals = ['🥇', '🥈', '🥉']

function ArtistCard({ artist, rank }) {
  if (!artist) {
    return null
  }

  const { name = 'Unknown Artist', similarity_score = 0, voice_type, genre } = artist

  const getBarColor = (score) => {
    if (score >= 80) return 'bg-green-400'
    if (score >= 60) return 'bg-primary'
    if (score >= 40) return 'bg-amber-400'
    return 'bg-orange-400'
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: rank * 0.1 }}
      className="p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors"
    >
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-lg">
          {rank <= 3 ? medals[rank - 1] : rank}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-slate-800 truncate">{name}</div>
          <div className="text-xs text-slate-400">{genre || voice_type || 'N/A'}</div>
        </div>
        <div className="text-right">
          <div className="font-mono font-semibold text-slate-700">{Math.round(similarity_score)}%</div>
        </div>
      </div>
      <div className="mt-2 h-1 rounded-full bg-slate-200 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${getBarColor(similarity_score)}`}
          initial={{ width: 0 }}
          animate={{ width: `${similarity_score}%` }}
          transition={{ duration: 0.5, delay: 0.2 + rank * 0.1 }}
        />
      </div>
    </motion.div>
  )
}

export default ArtistCard
