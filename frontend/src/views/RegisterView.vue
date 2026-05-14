<template>
  <div class="login-wrapper">
    <div class="login-card">
      <h2 class="title">Регистрация</h2>

      <form @submit.prevent="register" class="form">
        <input
          v-model="username"
          placeholder="Логин"
          @input="checkUsername"
          class="input"
          required
        />

        <p v-if="usernameTaken" class="error">Логин уже занят</p>

        <input
          v-model="password"
          placeholder="Пароль"
          type="password"
          class="input"
          required
        />

        <p v-if="password.length > 0 && password.length < 8" class="error">
          Минимум 8 символов
        </p>

        <input
          v-model="displayName"
          placeholder="Отображаемое имя"
          class="input"
          required
        />

        <input
          v-model="birthDate"
          type="date"
          class="input"
          required
        />

        <button class="button" :disabled="!canSubmit">
          {{ isLoading ? 'Создание...' : 'Создать аккаунт' }}
        </button>

        <p v-if="error" class="error">{{ error }}</p>
      </form>

      <p class="switch-link">
        Уже есть аккаунт?
        <router-link to="/login">Войти</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { useRegister } from '../composables/useRegister'

const {
  username,
  password,
  displayName,
  birthDate,
  error,
  usernameTaken,
  isLoading,
  canSubmit,
  checkUsername,
  register
} = useRegister()
</script>

<style scoped src="../styles/auth-form.css"></style>