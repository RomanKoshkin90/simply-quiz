import { useRef, useEffect, useCallback } from 'react'

function Spectrogram({ analyser, isActive }) {
  const canvasRef = useRef(null)
  const animationRef = useRef(null)
  const imageDataRef = useRef(null)
  
  const draw = useCallback(() => {
    if (!canvasRef.current || !analyser || !isActive) return
    
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const width = canvas.width
    const height = canvas.height
    
    // Получаем частотные данные
    const bufferLength = analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    analyser.getByteFrequencyData(dataArray)
    
    // Сдвигаем предыдущее изображение влево
    if (imageDataRef.current) {
      ctx.putImageData(imageDataRef.current, -1, 0)
    }
    
    // Рисуем новую колонку справа
    const barWidth = 1
    const x = width - barWidth
    
    // Показываем только нижнюю часть спектра (голосовой диапазон 0-2000 Hz)
    // FFT дает нам данные до Nyquist частоты (половина sample rate)
    // Для 44100 Hz это около 22050 Hz, нам нужна только малая часть
    const voiceRangeEnd = Math.floor(bufferLength * 0.1) // Примерно до 2000 Hz
    
    for (let i = 0; i < voiceRangeEnd; i++) {
      // Инвертируем Y чтобы низкие частоты были внизу
      const y = height - (i / voiceRangeEnd) * height
      const barHeight = height / voiceRangeEnd
      
      // Значение громкости (0-255)
      const value = dataArray[i]
      
      // Цветовая карта: от синего через голубой к белому
      const intensity = value / 255
      const r = Math.floor(14 + intensity * 220)  // 14 -> 234
      const g = Math.floor(165 + intensity * 80)  // 165 -> 245
      const b = Math.floor(233 + intensity * 22)  // 233 -> 255
      
      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`
      ctx.fillRect(x, y, barWidth, barHeight + 1)
    }
    
    // Заполняем верхнюю часть (высокие частоты) фоновым цветом
    ctx.fillStyle = '#f1f5f9'
    ctx.fillRect(x, 0, barWidth, height - (voiceRangeEnd / voiceRangeEnd) * height)
    
    // Сохраняем текущее изображение для следующего кадра
    imageDataRef.current = ctx.getImageData(0, 0, width, height)
    
    animationRef.current = requestAnimationFrame(draw)
  }, [analyser, isActive])
  
  useEffect(() => {
    if (!canvasRef.current) return
    
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    
    // Установка размеров canvas
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)
    canvas.width = rect.width
    canvas.height = rect.height
    
    // Очищаем canvas
    ctx.fillStyle = '#f1f5f9'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    
    if (isActive && analyser) {
      draw()
    }
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isActive, analyser, draw])
  
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-500 font-medium">Спектрограмма</span>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span>0 Hz</span>
          <div className="w-16 h-1.5 rounded-full bg-gradient-to-r from-primary/30 to-primary" />
          <span>~2 kHz</span>
        </div>
      </div>
      <canvas 
        ref={canvasRef}
        className="w-full h-24 rounded-lg"
        style={{ background: '#f1f5f9' }}
      />
      <div className="flex justify-between mt-1 text-[10px] text-slate-400">
        <span>← время</span>
        <span>интенсивность: тихо → громко</span>
      </div>
    </div>
  )
}

export default Spectrogram
