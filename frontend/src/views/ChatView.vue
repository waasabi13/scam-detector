<template>
  <div class="chat-container">
    <div class="main-content">
      <!-- Левая панель -->
      <div class="user-list-panel">
        <input
          ref="searchInputRef"
          v-model="search"
          placeholder="Поиск пользователей..."
          @input="searchUsers"
          class="search-input"
        />

        <!-- Результаты поиска -->
        <div class="user-results-widget" v-if="search">
          <div v-if="searchResults.length === 0" class="chat-placeholder">
            Пользователи не найдены
          </div>
          <div
            v-for="user in searchResults"
            :key="user.id"
            :class="['user-entry', { active: selectedUser?.id === user.id }]"
            @click="selectUser(user)"
          >
            <div class="avatar" :style="{ backgroundColor: getColor(user.username) }">
              {{ user.display_name?.charAt(0).toUpperCase() || 'U' }}
            </div>
            <div>
              <div class="display-name">{{ user.display_name || user.username }}</div>
              <div class="username">@{{ user.username }}</div>
            </div>
          </div>
        </div>

        <!-- Список чатов -->
        <ul class="chat-list" v-else>
          <li
            v-for="user in chatUsers"
            :key="user.id"
            :class="{ active: selectedUser?.id === user.id }"
            @click="selectUser(user)"
          >
            <div class="avatar" :style="{ backgroundColor: getColor(user.username) }">
              {{ user.display_name?.charAt(0).toUpperCase() || 'U' }}
            </div>
            <div>
              <div class="display-name">{{ user.display_name || user.username }}</div>
              <div class="username">@{{ user.username }}</div>
            </div>
          </li>
        </ul>

        <!-- Профиль -->
        <div class="profile-bar" @click="toggleProfileMenu">
          <div class="profile-avatar">👤</div>
          <div class="profile-info">
            <div class="display-name">{{ currentUser.display_name }}</div>
            <div class="username">@{{ currentUser.username }}</div>
          </div>
        </div>

        <div v-if="showProfileMenu" class="profile-menu" ref="profileMenuRef">
          <button @click="switchTab('chats')">Чаты</button>
          <button @click="switchTab('settings')">Настройки</button>
          <button @click="logout">Выход</button>
        </div>
      </div>

      <!-- Правая панель -->
      <div class="chat-panel">
        <div v-if="!selectedUser" class="empty-state">
          <p>Выберите пользователя, чтобы начать переписку</p>
        </div>

        <div v-else class="chat-box">
          <div class="chat-header">
            <div class="chat-header-info">
              <div class="avatar" :style="{ backgroundColor: getColor(selectedUser.username) }">
                {{ selectedUser.display_name?.charAt(0).toUpperCase() || 'U' }}
              </div>
              <h4>{{ selectedUser.display_name || selectedUser.username }}</h4>
            </div>
            <div class="chat-actions">
              <button @click="toggleDropdown">⋯</button>
              <div v-if="dropdownOpen" class="dropdown">
                <button @click="blockUser">Заблокировать</button>
                <button @click="clearChat">Очистить чат</button>
              </div>
            </div>
          </div>
            <div v-if="toast.visible" class="top-toast">
              {{ toast.text }}
            </div>
          <!-- Уведомление о мошенничестве -->
          <div v-if="showFraudAlert" class="fraud-alert">
            ⚠️ <strong>Внимание!</strong> Этот пользователь подозревается в мошенничестве.
            Не сообщайте личные данные и не переходите по ссылкам.
            <button class="close-alert" @click="hideFraudAlert">✖</button>
          </div>

          <div class="messages" ref="messagesContainer">
            <div
              v-for="msg in messages"
              :key="msg.id"
              :class="['message', msg.isMine ? 'mine' : 'theirs']"
              @contextmenu.prevent="openMessageMenu($event, msg)"
            >
              <div>{{ msg.text }}</div>
              <div class="timestamp">
                <span class="time">{{ formatTime(msg.timestamp) }}</span>
                <template v-if="msg.isMine">
                  <svg
                    v-if="msg.isRead"
                    class="msg-check"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                  >
                    <path d="M1 13l4 4L20 4" stroke="green" stroke-width="2" fill="none"/>
                  </svg>
                  <svg
                    v-else
                    class="msg-check"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                  >
                    <path d="M1 13l4 4L20 4" stroke="#999" stroke-width="2" fill="none"/>
                  </svg>
                </template>
              </div>
            </div>
          </div>
          <div
              v-if="messageMenu.visible"
              class="message-context-menu"
              :style="{ top: messageMenu.y + 'px', left: messageMenu.x + 'px' }"
            >
              <button @click="reportMessage">Пожаловаться на сообщение</button>
            </div>
          <form @submit.prevent="sendMessage" class="message-input">
            <input v-model="newMessage" placeholder="Введите сообщение..." required />
            <button type="submit">Отправить</button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import axios from '../api/axios'

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

const currentUser = ref({
  username: localStorage.getItem('username') || 'user',
  display_name: localStorage.getItem('display_name') || 'Вы',
  id: parseInt(localStorage.getItem('user_id')) || null
})

const fraudFlags = ref({})
const showFraudAlert = ref(false)

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
  const token = localStorage.getItem('token')
  const wsUrl = `${protocol}://${window.location.host}/ws/chat/${roomName}/`;


  socket = new WebSocket(wsUrl)

  socket.onopen = () => console.log('✅ WebSocket открыт:', wsUrl)

socket.onmessage = async (event) => {
  const data = JSON.parse(event.data)
  console.log('Пришло сообщение по WebSocket:', data)

  const isIncoming = data.sender !== currentUser.value.username
  const userId = selectedUser.value?.id

    const messageId = data.id || Date.now()

    messages.value.push({
      id: messageId,
      text: data.message,
      isMine: !isIncoming,
      timestamp: new Date().toISOString(),
      is_fraud: data.is_fraud && isIncoming
    })

    if (data.is_fraud && isIncoming && userId) {
      const hiddenAlerts = JSON.parse(localStorage.getItem('hiddenFraudAlerts') || '{}')

      if (!hiddenAlerts[messageId]) {
        showFraudAlert.value = true
      }
    }

  await nextTick()
  scrollToBottom()
  await loadDialogs()
}

  socket.onclose = () => {
    console.warn('⚠️ WebSocket закрыт, пробуем переподключиться...')
    setTimeout(connectWebSocket, 1000)
  }

  socket.onerror = (err) => {
    console.error('WebSocket ошибка:', err)
  }
}

const sendWebSocketMessage = (text) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
          message: text,
          sender: currentUser.value.username
        }))
    console.log('WebSocket message отправлено от:', currentUser.value.username)
  } else {
    console.warn('WebSocket не подключен или закрыт')
  }
}

const sendMessage = async () => {
  if (!newMessage.value.trim()) return;
  try {
    await axios.post(`/messages/${selectedUser.value.id}/send/`, {
      text: newMessage.value,
    })

    sendWebSocketMessage(newMessage.value)
    newMessage.value = ''

    await nextTick()
    scrollToBottom()
  } catch (err) {
    console.error('Ошибка отправки сообщения', err)
  }
}

const loadDialogs = async () => {
  try {
    const res = await axios.get('/chats/')
    chatUsers.value = res.data
  } catch (err) {
    console.error('Ошибка загрузки чатов', err)
  }
}

const fetchMessages = async (force = false) => {
  if (!selectedUser.value) return
  try {
    const res = await axios.get(`/messages/${selectedUser.value.id}/`)
    messages.value = res.data.map(msg => ({
      ...msg,
      isMine: msg.sender === currentUser.value.username
    }))
const checkForFraudMessages = (msgs) => {
  const hiddenAlerts = JSON.parse(localStorage.getItem('hiddenFraudAlerts') || '{}')

  const hasVisibleFraud = msgs.some(msg => {
    return msg.is_fraud && !hiddenAlerts[msg.id]
  })

  showFraudAlert.value = hasVisibleFraud
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

const showToast = (text) => {
  toast.value.text = text
  toast.value.visible = true

  setTimeout(() => {
    toast.value.visible = false
    toast.value.text = ''
  }, 2500)
}

const reportMessage = () => {
  closeMessageMenu()
  showToast('Ваше замечание учтено')
}
const selectUser = (user) => {
  selectedUser.value = user
  dropdownOpen.value = false
  fetchMessages(true)
  connectWebSocket()
}

const checkForFraudMessages = (msgs, force = false) => {
  const userId = selectedUser.value?.id
  if (!userId) return

  const hiddenAlerts = JSON.parse(localStorage.getItem('hiddenFraudAlerts') || '{}')
  const isHidden = hiddenAlerts[userId]

  const alreadyDetected = fraudFlags.value[userId]
  const hasFraud = msgs.some(m => m.is_fraud)

  if (hasFraud && !alreadyDetected) {
    fraudFlags.value[userId] = true
  }

  if ((hasFraud || fraudFlags.value[userId]) && !isHidden) {
    showFraudAlert.value = true
  }

  if (force) {
    showFraudAlert.value = (fraudFlags.value[userId] || hasFraud) && !isHidden
  }
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
  setInterval(() => {
    if (!selectedUser.value) loadDialogs()
  }, 10000)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  stopPolling()
})
</script>




<style scoped src="../styles/chat.css"></style>
