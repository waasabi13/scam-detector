<template>
  <div class="login-wrapper">
    <div class="login-card">
      <h2 class="title">Регистрация</h2>
      <form @submit.prevent="register" class="form">
        <input v-model="username" placeholder="Логин" @input="checkUsername" class="input" required />
        <p v-if="usernameTaken" class="error">Логин уже занят</p>

        <input v-model="password" placeholder="Пароль" type="password" class="input" required />
        <p v-if="password.length > 0 && password.length < 8" class="error">Минимум 8 символов</p>

        <input v-model="displayName" placeholder="Отображаемое имя" class="input" required />
        <input
          v-model="birthDate"
          type="date"
          class="input"
          placeholder="Дата рождения"
          required
        />

        <button class="button" :disabled="!canSubmit">Создать аккаунт</button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>

      <p class="switch-link">
        Уже есть аккаунт?
        <router-link to="/register">Войти</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from '../api/axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref('')
const password = ref('')
const displayName = ref('')
const birthDate = ref('')
const error = ref('')
const usernameTaken = ref(false)

const checkUsername = async () => {
  if (!username.value) return
  try {
    const res = await axios.get(`/users/check_username/?username=${username.value}`)
    usernameTaken.value = res.data.taken
  } catch {
    usernameTaken.value = false
  }
}

const canSubmit = computed(() => {
  return (
    username.value &&
    password.value.length >= 8 &&
    displayName.value &&
    birthDate.value &&
    !usernameTaken.value
  )
})

const register = async () => {
  try {
    const response = await axios.post('/register/', {
      username: username.value,
      password: password.value,
      display_name: displayName.value,
      birth_date: birthDate.value
    })

    localStorage.setItem("user_id", response.data.user_id)
    localStorage.setItem('token', response.data.token)
    localStorage.setItem('username', response.data.username)
    localStorage.setItem('display_name', response.data.display_name)

    router.push('/chat')
  } catch (err) {
    error.value = err.response?.data?.error || 'Ошибка регистрации'
  }
}

</script>

<style scoped src="../styles/auth-form.css" />
