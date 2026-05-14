import { ref } from 'vue'

export function useToast() {
  const toast = ref({
    visible: false,
    text: ''
  })

  let timer = null

  const showToast = (text, duration = 2500) => {
    toast.value.text = text
    toast.value.visible = true

    if (timer) {
      clearTimeout(timer)
    }

    timer = setTimeout(() => {
      toast.value.visible = false
      toast.value.text = ''
    }, duration)
  }

  return {
    toast,
    showToast
  }
}