import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useToast } from './useToast'
import { useWebSocket } from './useWebSocket'
import axios from '../api/axios'

export function useChat() {
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

  const showFraudAlert = ref(false)
  const fraudFlags = ref({})

  const mediaRecorder = ref(null)
  const audioChunks = ref([])
  const isRecording = ref(false)

  const { toast, showToast } = useToast()
  const { connect, send, disconnect } = useWebSocket()

  const messageMenu = ref({
    visible: false,
    x: 0,
    y: 0,
    message: null
  })

  const currentUser = ref({
    username: localStorage.getItem('username') || 'user',
    display_name: localStorage.getItem('display_name') || 'Вы',
    id: parseInt(localStorage.getItem('user_id')) || null
  })

  const getHiddenAlerts = () => {
    return JSON.parse(localStorage.getItem('hiddenFraudAlerts') || '{}')
  }

  const saveHiddenAlerts = (hiddenAlerts) => {
    localStorage.setItem('hiddenFraudAlerts', JSON.stringify(hiddenAlerts))
  }

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

    connect({
      currentUserId: currentUser.value.id,
      selectedUserId: selectedUser.value.id,
      onMessage: handleSocketMessage
    })
  }

  const handleSocketMessage = async (data) => {
    const isIncoming = data.sender !== currentUser.value.username
    const messageId = data.id || Date.now()

    messages.value.push({
      id: messageId,
      text: data.message,
      isMine: !isIncoming,
      timestamp: new Date().toISOString(),
      is_fraud: Boolean(data.is_fraud) && isIncoming,
      message_type: data.message_type || 'text',
      audio_url: data.audio_url || null,
      transcript: data.transcript || ''
    })

    if (Boolean(data.is_fraud) && isIncoming) {
      const hiddenAlerts = getHiddenAlerts()

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

  const sendWebSocketMessage = (text) => {
    send({
      message: text,
      sender: currentUser.value.username
    })
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
        isMine: msg.sender === currentUser.value.username,
        is_fraud: Boolean(msg.is_fraud) && msg.sender !== currentUser.value.username,
        showTranscript: false,
        message_type: msg.message_type || 'text',
        audio_url: msg.audio_url || null,
        transcript: msg.transcript || ''
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
    const hiddenAlerts = getHiddenAlerts()

    showFraudAlert.value = msgs.some(msg => {
      return Boolean(msg.is_fraud) && !msg.isMine && !hiddenAlerts[msg.id]
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
    showFraudAlert.value = false
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

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      audioChunks.value = []

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'

      mediaRecorder.value = new MediaRecorder(stream, { mimeType })

      mediaRecorder.value.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.value.push(event.data)
        }
      }

      mediaRecorder.value.onstop = async () => {
        await new Promise(resolve => setTimeout(resolve, 300))

        stream.getTracks().forEach(track => track.stop())

        if (!audioChunks.value.length) {
          showToast('Запись не содержит аудио')
          return
        }

        const audioBlob = new Blob(audioChunks.value, { type: mimeType })

        console.log('audioBlob size:', audioBlob.size)

        if (audioBlob.size < 5000) {
          showToast('Запись слишком короткая')
          return
        }

        const audioFile = new File(
          [audioBlob],
          `voice_${Date.now()}.webm`,
          { type: mimeType }
        )

        await sendVoiceMessage(audioFile)
      }

      mediaRecorder.value.start()
      isRecording.value = true
      showToast('Запись началась')
    } catch (err) {
      console.error('Ошибка записи аудио', err)
      showToast('Не удалось получить доступ к микрофону')
    }
  }

  const stopVoiceRecording = () => {
    if (mediaRecorder.value && mediaRecorder.value.state === 'recording') {
      mediaRecorder.value.requestData()

      setTimeout(() => {
        mediaRecorder.value.stop()
        isRecording.value = false
        showToast('Запись отправляется')
      }, 300)
    }
  }

  const toggleVoiceRecording = async () => {
    if (isRecording.value) {
      stopVoiceRecording()
    } else {
      await startVoiceRecording()
    }
  }

  const sendVoiceMessage = async (file) => {
    if (!file || !selectedUser.value) return

    const formData = new FormData()
    formData.append('audio', file)

    console.log('file size before upload:', file.size, file.type)

    try {
      const res = await axios.post(
        `/messages/${selectedUser.value.id}/send-voice/`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )

      messages.value.push({
        ...res.data,
        isMine: true,
        message_type: res.data.message_type || 'voice',
        audio_url: res.data.audio_url || null,
        transcript: res.data.transcript || '',
        showTranscript: false
      })

      await nextTick()
      scrollToBottom()
      await loadDialogs()
    } catch (err) {
      console.error('Ошибка отправки голосового', err)
      showToast('Не удалось отправить голосовое сообщение')
    }
  }

  const checkVoiceMessage = async (msg) => {
    try {
      const res = await axios.post(`/messages/${msg.id}/check-voice/`)

      msg.transcript = res.data.transcript
      msg.showTranscript = true
      msg.is_fraud = res.data.is_fraud
      msg.fraud_confidence = res.data.fraud_confidence

      if (msg.is_fraud && !msg.isMine) {
        showFraudAlert.value = true
      }

      showToast('Голосовое сообщение проверено')
    } catch (err) {
      console.error('Ошибка проверки голосового сообщения', err)
      showToast('Не удалось проверить голосовое сообщение')
    }
  }

  const hideFraudAlert = () => {
    const hiddenAlerts = getHiddenAlerts()

    messages.value.forEach(msg => {
      if (msg.is_fraud && !msg.isMine) {
        hiddenAlerts[msg.id] = true
      }
    })

    saveHiddenAlerts(hiddenAlerts)
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

  const blockUser = () => {
    alert('(заглушка)')
  }

  const clearChat = () => {
    messages.value = []
  }

  const toggleTranscript = (msg) => {
  msg.showTranscript = !msg.showTranscript
  }

  const handleClickOutside = (event) => {
    closeMessageMenu()

    if (searchInputRef.value && !searchInputRef.value.contains(event.target)) {
      search.value = ''
      searchResults.value = []
    }

    if (
      showProfileMenu.value &&
      profileMenuRef.value &&
      !profileMenuRef.value.contains(event.target) &&
      !event.target.closest('.profile-bar')
    ) {
      showProfileMenu.value = false
    }
  }

  onMounted(() => {
    loadDialogs()
    document.addEventListener('click', handleClickOutside)

    pollingInterval.value = setInterval(() => {
      if (!selectedUser.value) {
        loadDialogs()
      }
    }, 10000)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', handleClickOutside)
    stopPolling()
    disconnect()
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
    logout,
    getColor,
    formatTime,
    toggleProfileMenu,
    toggleDropdown,
    switchTab,
    blockUser,
    clearChat,
    toggleTranscript,
    isRecording,
    toggleVoiceRecording,
    sendVoiceMessage,
    checkVoiceMessage
  }
}