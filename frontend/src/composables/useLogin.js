import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from '../api/axios'

export function useLogin() {
  const router = useRouter()

  const username = ref('')
  const password = ref('')
  const error = ref('')
  const isLoading = ref(false)

  const login = async () => {
    error.value = ''

    if (!username.value.trim() || !password.value.trim()) {
      error.value = 'Введите имя пользователя и пароль'
      return
    }

    try {
      isLoading.value = true

      const response = await axios.post('/login/', {
        username: username.value,
        password: password.value
      })

      localStorage.setItem('user_id', response.data.user_id)
      localStorage.setItem('token', response.data.token)
      localStorage.setItem('username', response.data.username)
      localStorage.setItem('display_name', response.data.display_name)

      router.push('/chat')
    } catch (err) {
      error.value = err.response?.data?.error || 'Ошибка входа'
    } finally {
      isLoading.value = false
    }
  }

  return {
    username,
    password,
    error,
    isLoading,
    login
  }
}