function BackgroundEffects() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
      {/* Простой градиентный фон */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-sky-50" />
      
      {/* Легкие декоративные круги */}
      <div className="absolute -top-20 -right-20 w-80 h-80 bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 -left-20 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
    </div>
  )
}

export default BackgroundEffects
