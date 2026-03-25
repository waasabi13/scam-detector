<template>
  <div class="login-wrapper">
    <div class="login-card">
      <h2 class="title">Вход</h2>
      <form @submit.prevent="login" class="form">
        <input
          type="text"
          v-model="username"
          placeholder="Имя пользователя"
          class="input"
          required
        />
        <input
          type="password"
          v-model="password"
          placeholder="Пароль"
          class="input"
          required
        />
        <button type="submit" class="button">Войти</button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>
      <p class="switch-link">
        Еще нет аккаунта?
        <router-link to="/register">Зарегистрироваться</router-link>
      </p>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import { useRouter } from "vue-router";
import { ref } from "vue";

export default {
  name: "LoginView",
  setup() {
    const router = useRouter();
    const username = ref("");
    const password = ref("");
    const error = ref("");

    const login = async () => {
      try {
        const response = await axios.post("http://127.0.0.1:8000/api/login/", {
          username: username.value,
          password: password.value,
        })
        localStorage.setItem("user_id", response.data.user_id)
        localStorage.setItem('token', response.data.token)
        localStorage.setItem('username', response.data.username)
        localStorage.setItem('display_name', response.data.display_name)

        router.push('/chat')
      } catch (err) {
        error.value = err.response?.data?.error || 'Ошибка входа'
      }
    }


    return { username, password, error, login };
  },
};
</script>

<style scoped src="../styles/auth-form.css"></style>
