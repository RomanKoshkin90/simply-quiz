import { useState } from 'react'
import { Music, Star, ExternalLink, Headphones } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

function SongCard({ song, isLocked = false }) {
  if (!song) {
    return null
  }

  const {
    title = 'Unknown Song',
    artist_name = 'Unknown Artist',
    pitch_match_score = 0,
    difficulty,
    yandex_music_id,
    yandex_music_url
  } = song
  const [showPlayer, setShowPlayer] = useState(false)

  return (
    <div className="group rounded-xl bg-slate-50/80 backdrop-blur-md hover:bg-slate-100/80 transition-colors overflow-hidden relative">
      <div className={`p-3 ${isLocked ? 'blur-md pointer-events-none' : ''}`}>
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Music className="w-4 h-4 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-slate-800 truncate">{title}</div>
            <div className="text-xs text-slate-400 truncate">{artist_name}</div>
            <div className="flex items-center gap-2 mt-1">
{/*               {pitch_match_score > 0 && ( */}
{/*                 <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary"> */}
{/*                   {Math.round(pitch_match_score)}% */}
{/*                 </span> */}
{/*               )} */}
{/*               {difficulty && ( */}
{/*                 <div  */}
{/*                   className="flex gap-0.5" */}
{/*                   title={`Сложность: ${difficulty}/5 ${difficulty === 1 ? '(легкая)' : difficulty === 2 ? '(средняя)' : difficulty === 3 ? '(выше среднего)' : difficulty === 4 ? '(сложная)' : '(очень сложная)'}`} */}
{/*                 > */}
{/*                   {[...Array(5)].map((_, i) => ( */}
{/*                     <Star */}
{/*                       key={i} */}
{/*                       className={`w-3 h-3 ${i < difficulty ? 'text-amber-400 fill-amber-400' : 'text-slate-200'}`} */}
{/*                     /> */}
{/*                   ))} */}
{/*                 </div> */}
{/*               )} */}
            </div>
          </div>
          
          {/* Кнопки действий */}
          <div className="flex gap-1 flex-shrink-0">
            {yandex_music_url && (
              <>
                <button
                  onClick={() => setShowPlayer(!showPlayer)}
                  className="p-1.5 rounded-[40px] hover:bg-white/80 transition-colors"
                  title={showPlayer ? "Скрыть плеер" : "Послушать"}
                >
                  <Headphones className={`w-4 h-4 ${showPlayer ? 'text-primary' : 'text-slate-400'}`} />
                </button>
                <a
                  href={yandex_music_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-lg hover:bg-white/80 transition-colors"
                  title="Открыть в Яндекс Музыке"
                >
                  <ExternalLink className="w-4 h-4 text-slate-400 hover:text-primary" />
                </a>
              </>
            )}
            {!yandex_music_url && (
              <a
                href={`https://music.yandex.ru/search?text=${encodeURIComponent(artist_name + ' ' + title)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-lg hover:bg-white/80 transition-colors text-xs text-slate-400 hover:text-primary"
                title="Искать в Яндекс Музыке"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Яндекс Музыка iframe плеер */}
      <AnimatePresence>
        {showPlayer && yandex_music_url && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3">
              <iframe
                src={yandex_music_url.replace('/track/', '/iframe/#track/')}
                width="100%"
                height="152"
                frameBorder="0"
                allow="autoplay"
                className="rounded-lg"
                style={{ minHeight: '152px' }}
              />
              <p className="text-xs text-slate-400 mt-2 text-center">
                Если плеер не загрузился, <a href={yandex_music_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">открой в Яндекс Музыке</a>
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default SongCard
