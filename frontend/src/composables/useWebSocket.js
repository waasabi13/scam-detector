export function useWebSocket() {
  let socket = null

  const connect = ({ currentUserId, selectedUserId, onMessage }) => {
    if (!currentUserId || !selectedUserId) return

    disconnect()

    const ids = [currentUserId, selectedUserId].sort((a, b) => a - b)
    const roomName = `${ids[0]}_${ids[1]}`
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.host}/ws/chat/${roomName}/`

    socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      console.log('WebSocket открыт:', wsUrl)
    }

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      onMessage(data)
    }

    socket.onclose = () => {
      console.warn('WebSocket закрыт')
    }

    socket.onerror = (err) => {
      console.error('WebSocket ошибка:', err)
    }
  }

  const send = (payload) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket не подключен или закрыт')
      return
    }

    socket.send(JSON.stringify(payload))
  }

  const disconnect = () => {
    if (socket) {
      socket.onclose = null
      socket.close()
      socket = null
    }
  }

  return {
    connect,
    send,
    disconnect
  }
}