<template>
  <div class="chat-container">
    <div class="main-content">
      <div class="user-list-panel">
        <input
          ref="searchInputRef"
          v-model="search"
          placeholder="Поиск пользователей..."
          @input="searchUsers"
          class="search-input"
        />

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

        <ul class="chat-list" v-else>
          <li
            v-for="user in chatUsers"
            :key="user.id"
            :class="{
              active: selectedUser?.id === user.id,
              unread: user.unread_count > 0
            }"
            @click="selectUser(user)"
          >
            <div class="avatar" :style="{ backgroundColor: getColor(user.username) }">
              {{ user.display_name?.charAt(0).toUpperCase() || 'U' }}
            </div>

            <div class="user-text">
              <div :class="['display-name', { unread: user.unread_count > 0 }]">
                {{ user.display_name || user.username }}
              </div>
              <div class="username">@{{ user.username }}</div>
            </div>

            <span v-if="user.unread_count > 0" class="unread-dot"></span>
          </li>
        </ul>

        <div class="profile-bar" @click="toggleProfileMenu">
          <div class="profile-avatar">👤</div>
          <div class="profile-info">
            <div class="display-name">{{ currentUser.display_name }}</div>
            <div class="username">@{{ currentUser.username }}</div>
          </div>
        </div>

        <div v-if="showProfileMenu" class="profile-menu" ref="profileMenuRef">
          <button @click="switchTab">Чаты</button>
          <button @click="switchTab">Настройки</button>
          <button @click="logout">Выход</button>
        </div>
      </div>

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
              <div v-if="msg.message_type === 'voice'" class="voice-message">
                <audio :src="msg.audio_url" controls></audio>

                <button
                  class="check-voice-button"
                  @click="checkVoiceMessage(msg)"
                >
                  Проверить
                </button>

                <button
                  v-if="msg.transcript"
                  class="transcript-toggle"
                  @click="toggleTranscript(msg)"
                >
                  {{ msg.showTranscript ? 'Скрыть расшифровку' : 'Показать расшифровку' }}
                </button>

                <div
                  v-if="msg.transcript && msg.showTranscript"
                  class="voice-transcript-box"
                >
                  {{ msg.transcript }}
                </div>
              </div>

              <div v-else>
                {{ msg.text }}
              </div>

              <div class="timestamp">
                <span class="time">{{ formatTime(msg.timestamp) }}</span>

                <template v-if="msg.isMine">
                  <svg
                    v-if="msg.isRead"
                    class="msg-check"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                  >
                    <path d="M1 13l4 4L20 4" stroke="green" stroke-width="2" fill="none" />
                  </svg>

                  <svg
                    v-else
                    class="msg-check"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                  >
                    <path d="M1 13l4 4L20 4" stroke="#999" stroke-width="2" fill="none" />
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

          <form @submit.prevent="handleSendMessage" class="message-input">
            <textarea
              ref="messageInputRef"
              v-model="newMessage"
              placeholder="Введите сообщение..."
              rows="1"
              class="message-textarea"
              required
              @input="autoResizeMessageInput"
              @keydown.enter.exact.prevent="handleSendMessage"
              @keydown.shift.enter.stop
            ></textarea>

            <button
              type="button"
              class="voice-button"
              :class="{ recording: isRecording }"
              @click="toggleVoiceRecording"
              title="Голосовое сообщение"
            >
              <svg
                v-if="!isRecording"
                class="voice-icon"
                viewBox="0 0 24 24"
                fill="none"
              >
                <path
                  d="M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                />
                <path
                  d="M5 10.5a7 7 0 0 0 14 0"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                />
                <path
                  d="M12 17.5V21"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                />
              </svg>

              <span v-else class="record-dot"></span>
            </button>

            <button type="submit">Отправить</button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { useChat } from '../composables/useChat'

const messageInputRef = ref(null)

const {
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
  showFraudAlert,
  messageMenu,
  toast,

  sendMessage,
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

  isRecording,
  toggleVoiceRecording,
  checkVoiceMessage,
  toggleTranscript
} = useChat()

const autoResizeMessageInput = () => {
  const textarea = messageInputRef.value

  if (!textarea) return

  textarea.style.height = 'auto'
  textarea.style.height = `${textarea.scrollHeight}px`
}

const resetMessageInputHeight = async () => {
  await nextTick()

  const textarea = messageInputRef.value

  if (!textarea) return

  textarea.style.height = 'auto'
}

const handleSendMessage = async () => {
  if (!newMessage.value.trim()) return

  await sendMessage()
  await resetMessageInputHeight()
}
</script>

<style scoped src="../styles/chat.css"></style>