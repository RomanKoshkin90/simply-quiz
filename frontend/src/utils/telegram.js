const TELEGRAM_BOT_TOKEN = '8408102586:AAEP9p5SDgLxaIol02B0qkBIESFZbdYXJsM'
const TELEGRAM_CHAT_ID = '-5281969218'

export const sendToTelegram = async (data) => {
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
