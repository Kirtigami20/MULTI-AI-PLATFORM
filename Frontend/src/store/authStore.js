import { create } from 'zustand'
import { authAPI } from '../api/auth'

const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('token') || null,
  loading: true,

  init: async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      set({ loading: false })
      return
    }
    try {
      const { data } = await authAPI.me()
      set({ user: data, token, loading: false })
    } catch {
      localStorage.removeItem('token')
      set({ user: null, token: null, loading: false })
    }
  },

  login: async (email, password) => {
    const { data } = await authAPI.login({ email, password })
    localStorage.setItem('token', data.access_token)
    set({ token: data.access_token })
    const me = await authAPI.me()
    set({ user: me.data })
    return data
  },

  register: async (name, email, password) => {
    const { data } = await authAPI.register({ name, email, password })
    return data
  },

  logout: () => {
    localStorage.removeItem('token')
    set({ user: null, token: null })
  },
}))

export default useAuthStore
