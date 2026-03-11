import { motion } from 'framer-motion'
import { Mic2, RotateCcw, SquareArrowOutUpRight } from 'lucide-react'

function Header({ onReset, showReset }) {
  const handleShare = () => {
    navigator.clipboard.writeText('https://quiz.simplyonline.ru/')
    alert('Ссылка скопирована!')
  }

  return (
    <header className="py-6 px-4 bg-white border-b border-slate-200">
      <div className="container mx-auto flex items-center justify-between">
        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Mic2 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-display font-bold text-2xl text-[#72AEF7]">
              СИМПЛИ
            </h1>
            <p className="text-slate-500 text-sm">Анализ голоса</p>
          </div>
        </motion.div>

        <div className="flex items-center gap-2">
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={handleShare}
            className="flex items-center gap-2 px-4 py-2 transition-opacity hover:opacity-70"
          >
            <SquareArrowOutUpRight className="w-4 h-4 text-black" />
            <span className="text-black text-sm">
              Поделиться
            </span>
          </motion.button>

          {showReset && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={onReset}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition-all group"
            >
              <RotateCcw className="w-4 h-4 text-slate-500 group-hover:text-primary transition-colors" />
              <span className="text-slate-600 group-hover:text-slate-800 text-sm">
                Новый анализ
              </span>
            </motion.button>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header
