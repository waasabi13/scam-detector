import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import axios from '../api/axios'

export function useChat() {
  let socket = null

  const search = ref('')
  const searchResults = ref([])
  const chatUsers = ref([])
  const selectedUser = ref(null)
  const messages = ref([])
  const newMessage = ref('')
  const showProfileMenu = ref(false)
  const dropdownOpen = ref(false)
  const searchInputRef = ref(null)
  const profileMenuRef = ref(null)
  const messagesContainer = ref(null)
  const pollingInterval = ref(null)

  const fraudFlags = ref({})
  const showFraudAlert = ref(false)

  const messageMenu = ref({
    visible: false,
    x: 0,
    y: 0,
    message: null
  })

  const toast = ref({
    visible: false,
    text: ''
  })

  const currentUser = ref({
    username: localStorage.getItem('username') || 'user',
    display_name: localStorage.getItem('display_name') || 'Вы',
    id: parseInt(localStorage.getItem('user_id')) || null
  })

  const loadDialogs = async () => {
    try {
      const res = await axios.get('/chats/')
      chatUsers.value = res.data
    } catch (err) {
      console.error('Ошибка загрузки чатов', err)
    }
  }

  const connectWebSocket = () => {
    if (!selectedUser.value || !currentUser.value.id) return

    if (socket) {
      socket.onclose = null
      socket.close()
      socket = null
    }

    const ids = [currentUser.value.id, selectedUser.value.id].sort((a, b) => a - b)
    const roomName = `${ids[0]}_${ids[1]}`
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.host}/ws/chat/${roomName}/`

    socket = new WebSocket(wsUrl)

    socket.onopen = () => console.log('WebSocket открыт:', wsUrl)

    socket.onmessage = async (event) => {
      const data = JSON.parse(event.data)

      const isIncoming = data.sender !== currentUser.value.username
      const messageId = data.id || Date.now()

      messages.value.push({
        id: messageId,
        text: data.message,
        isMine: !isIncoming,
        timestamp: new Date().toISOString(),
        is_fraud: data.is_fraud && isIncoming
      })

      if (data.is_fraud === true && isIncoming) {
        const hiddenAlerts = JSON.parse(localStorage.getItem('hiddenFraudAlerts') || '{}')

        if (!hiddenAlerts[messageId]) {
          showFraudAlert.value = true
        }
      }

      if (isIncoming && selectedUser.value) {
        const dialog = chatUsers.value.find(user => user.id === selectedUser.value.id)

        if (dialog) {
          dialog.unread_count = (dialog.unread_count || 0) + 1
          chatUsers.value = [
            dialog,
            ...chatUsers.value.filter(user => user.id !== dialog.id)
          ]
        }
      }

      await nextTick()
      scrollToBottom()
      await loadDialogs()
    }

    socket.onclose = () => {
      console.warn('WebSocket закрыт, пробуем переподключиться...')
      setTimeout(connectWebSocket, 1000)
    }

    socket.onerror = (err) => {
      console.error('WebSocket ошибка:', err)
    }
  }

  const sendWebSocketMessage = (text) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket не подключен или закрыт')
      return
    }

    socket.send(JSON.stringify({
      message: text,
      sender: currentUser.value.username
    }))
  }

  const sendMessage = async () => {
    if (!newMessage.value.trim() || !selectedUser.value) return

    try {
      await axios.post(`/messages/${selectedUser.value.id}/send/`, {
        text: newMessage.value
      })

      sendWebSocketMessage(newMessage.value)
      newMessage.value = ''

      await nextTick()
      scrollToBottom()
    } catch (err) {
      console.error('Ошибка отправки сообщения', err)
    }
  }

  const fetchMessages = async () => {
    if (!selectedUser.value) return

    try {
      const res = await axios.get(`/messages/${selectedUser.value.id}/`)

      messages.value = res.data.map(msg => ({
        ...msg,
        isMine: msg.sender === currentUser.value.username
      }))

      checkForFraudMessages(messages.value)

      await loadDialogs()
      await nextTick()
      scrollToBottom()
    } catch (err) {
      console.error('Ошибка загрузки сообщений', err)
    }
  }

  const checkForFraudMessages = (msgs) => {
    const hiddenAlerts = JSON.parse(localStorage.getItem('hiddenFraudAlerts') || '{}')

    showFraudAlert.value = msgs.some(msg => {
      return msg.is_fraud && !hiddenAlerts[msg.id]
    })
  }

  const searchUsers = async () => {
    if (!search.value.trim()) {
      searchResults.value = []
      return
    }

    try {
      const res = await axios.get(`/users/search/?q=${encodeURIComponent(search.value)}`)
      searchResults.value = res.data
    } catch (err) {
      console.error('Ошибка поиска пользователей', err)
    }
  }

  const selectUser = (user) => {
    selectedUser.value = user
    dropdownOpen.value = false
    user.unread_count = 0
    fetchMessages()
    connectWebSocket()
  }

  const openMessageMenu = (event, msg) => {
    messageMenu.value = {
      visible: true,
      x: event.clientX,
      y: event.clientY,
      message: msg
    }
  }

  const closeMessageMenu = () => {
    messageMenu.value.visible = false
    messageMenu.value.message = null
  }

  const reportMessage = async () => {
    if (!messageMenu.value.message?.id) return

    try {
      await axios.post(`/messages/${messageMenu.value.message.id}/report/`)
      closeMessageMenu()
      showToast('Ваше замечание учтено')
    } catch (err) {
      console.error('Ошибка отправки жалобы', err)
      showToast('Не удалось отправить жалобу')
    }
  }

  const showToast = (text) => {
    toast.value.text = text
    toast.value.visible = true

    setTimeout(() => {
      toast.value.visible = false
      toast.value.text = ''
    }, 2500)
  }

  const sendVoiceStub = () => {
    showToast('Голосовое сообщение подготовлено к отправке')
  }

  const hideFraudAlert = () => {
    const hiddenAlerts = JSON.parse(localStorage.getItem('hiddenFraudAlerts') || '{}')

    messages.value.forEach(msg => {
      if (msg.is_fraud) {
        hiddenAlerts[msg.id] = true
      }
    })

    localStorage.setItem('hiddenFraudAlerts', JSON.stringify(hiddenAlerts))
    showFraudAlert.value = false
  }

  const scrollToBottom = () => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }

  const logout = () => {
    localStorage.clear()
    window.location.href = '/login'
  }

  const getColor = (key) => {
    const colors = ['#FFA07A', '#8FBC8F', '#87CEFA', '#DDA0DD', '#FFD700']
    const hash = Array.from(key).reduce((acc, char) => acc + char.charCodeAt(0), 0)
    return colors[hash % colors.length]
  }

  const formatTime = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }

  const toggleProfileMenu = () => {
    showProfileMenu.value = !showProfileMenu.value
  }

  const toggleDropdown = () => {
    dropdownOpen.value = !dropdownOpen.value
  }

  const switchTab = () => {
    showProfileMenu.value = false
  }

  const stopPolling = () => {
    if (pollingInterval.value) {
      clearInterval(pollingInterval.value)
      pollingInterval.value = null
    }
  }

  const blockUser = () => alert('(заглушка)')
  const clearChat = () => (messages.value = [])

  const handleClickOutside = (e) => {
    closeMessageMenu()

    if (searchInputRef.value && !searchInputRef.value.contains(e.target)) {
      search.value = ''
      searchResults.value = []
    }

    if (
      showProfileMenu.value &&
      profileMenuRef.value &&
      !profileMenuRef.value.contains(e.target) &&
      !e.target.closest('.profile-bar')
    ) {
      showProfileMenu.value = false
    }
  }

  onMounted(() => {
    loadDialogs()
    document.addEventListener('click', handleClickOutside)

    pollingInterval.value = setInterval(() => {
      if (!selectedUser.value) loadDialogs()
    }, 10000)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', handleClickOutside)
    stopPolling()

    if (socket) {
      socket.close()
      socket = null
    }
  })

  return {
    search,
    searchResults,
    chatUsers,
    selectedUser,
    messages,
    newMessage,
    showProfileMenu,
    dropdownOpen,
    searchInputRef,
    profileMenuRef,
    messagesContainer,
    currentUser,
    fraudFlags,
    showFraudAlert,
    messageMenu,
    toast,

    connectWebSocket,
    sendMessage,
    loadDialogs,
    fetchMessages,
    searchUsers,
    selectUser,
    openMessageMenu,
    reportMessage,
    hideFraudAlert,
    sendVoiceStub,
    logout,
    getColor,
    formatTime,
    toggleProfileMenu,
    toggleDropdown,
    switchTab,
    blockUser,
    clearChat
  }
}