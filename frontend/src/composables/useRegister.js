import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from '../api/axios'

export function useRegister() {
  const router = useRouter()

  const username = ref('')
  const password = ref('')
  const displayName = ref('')
  const birthDate = ref('')
  const error = ref('')
  const usernameTaken = ref(false)
  const isLoading = ref(false)

  const checkUsername = async () => {
    if (!username.value.trim()) {
      usernameTaken.value = false
      return
    }

    try {
      const res = await axios.get(
        `/users/check_username/?username=${encodeURIComponent(username.value)}`
      )

      usernameTaken.value = res.data.taken
    } catch {
      usernameTaken.value = false
    }
  }

  const canSubmit = computed(() => {
    return (
      username.value.trim() &&
      password.value.length >= 8 &&
      displayName.value.trim() &&
      birthDate.value &&
      !usernameTaken.value &&
      !isLoading.value
    )
  })

  const register = async () => {
    error.value = ''

    if (!canSubmit.value) {
      error.value = 'Проверьте корректность заполнения формы'
      return
    }

    try {
      isLoading.value = true

      const response = await axios.post('/register/', {
        username: username.value,
        password: password.value,
        display_name: displayName.value,
        birth_date: birthDate.value
      })

      localStorage.setItem('user_id', response.data.user_id)
      localStorage.setItem('token', response.data.token)
      localStorage.setItem('username', response.data.username)
      localStorage.setItem('display_name', response.data.display_name)

      router.push('/chat')
    } catch (err) {
      error.value = err.response?.data?.error || 'Ошибка регистрации'
    } finally {
      isLoading.value = false
    }
  }

  return {
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
  }
}