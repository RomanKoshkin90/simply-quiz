import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion } from 'framer-motion'
import { Upload, Music, AlertCircle } from 'lucide-react'

function AudioUploader({ onUpload, error }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0])
    }
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac'],
    },
    maxFiles: 1,
  })

  return (
    <div className="max-w-xl mx-auto mt-8">
      {/* Заголовок */}
      <motion.div 
        className="text-center mb-10"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <h2 className="font-display font-bold text-3xl md:text-4xl text-slate-800 mb-3">
          Узнай свой голос
        </h2>
        <p className="text-slate-500 text-lg">
          Загрузи запись и получи детальный анализ диапазона и тембра
        </p>
      </motion.div>

      {/* Дропзона */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <div
          {...getRootProps()}
          className={`
            relative p-10 rounded-2xl cursor-pointer transition-all duration-200
            border-2 border-dashed bg-white
            ${isDragActive
              ? 'border-primary bg-primary/5 scale-[1.01]'
              : 'border-slate-200 hover:border-primary/50 hover:bg-slate-50'
            }
          `}
        >
          <input {...getInputProps()} />
          
          <div className="flex flex-col items-center text-center">
            <div className={`
              w-16 h-16 rounded-2xl mb-5 flex items-center justify-center transition-colors
              ${isDragActive ? 'bg-primary' : 'bg-primary/10'}
            `}>
              <Upload className={`w-7 h-7 ${isDragActive ? 'text-white' : 'text-primary'}`} />
            </div>
            
            <h3 className="font-semibold text-lg text-slate-800 mb-1">
              {isDragActive ? 'Отпусти для загрузки' : 'Перетащи аудио файл'}
            </h3>
            <p className="text-slate-500 mb-4">
              или нажми для выбора
            </p>
            
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Music className="w-4 h-4" />
              <span>WAV, MP3, FLAC, OGG — до 5 минут</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Ошибка */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-4 rounded-xl bg-red-50 border border-red-100 flex items-start gap-3"
        >
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-red-600 text-sm">{error}</p>
        </motion.div>
      )}

      {/* Фичи */}
      <motion.div 
        className="grid grid-cols-3 gap-3 mt-10"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        {[
          { icon: '🎵', title: 'Pitch', desc: 'CREPE' },
          { icon: '🎭', title: 'Тембр', desc: 'OpenSMILE' },
          { icon: '⭐', title: 'Матчинг', desc: 'AI' },
        ].map((feature, i) => (
          <div 
            key={i}
            className="p-4 rounded-xl bg-white border border-slate-100 text-center"
          >
            <div className="text-2xl mb-2">{feature.icon}</div>
            <div className="font-medium text-slate-700 text-sm">{feature.title}</div>
            <div className="text-slate-400 text-xs">{feature.desc}</div>
          </div>
        ))}
      </motion.div>
    </div>
  )
}

export default AudioUploader
