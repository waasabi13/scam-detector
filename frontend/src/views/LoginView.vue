<template>
  <div class="login-wrapper">
    <div class="login-card">
      <h2 class="title">Вход</h2>

      <form @submit.prevent="login" class="form">
        <input
          v-model="username"
          type="text"
          placeholder="Имя пользователя"
          class="input"
          required
        />

        <input
          v-model="password"
          type="password"
          placeholder="Пароль"
          class="input"
          required
        />

        <button type="submit" class="button" :disabled="isLoading">
          {{ isLoading ? 'Вход...' : 'Войти' }}
        </button>

        <p v-if="error" class="error">{{ error }}</p>
      </form>

      <p class="switch-link">
        Еще нет аккаунта?
        <router-link to="/register">Зарегистрироваться</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { useLogin } from '../composables/useLogin'

const {
  username,
  password,
  error,
  isLoading,
  login
} = useLogin()
</script>

<style scoped src="../styles/auth-form.css"></style>