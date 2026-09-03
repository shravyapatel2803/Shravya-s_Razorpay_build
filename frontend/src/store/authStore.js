import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      setAuth: ({ access_token, refresh_token, user }) =>
        set({ token: access_token, refreshToken: refresh_token, user, isAuthenticated: true }),

      setUser: (user) => set({ user }),

      setToken: (token) => set({ token }),

      logout: () =>
        set({ token: null, refreshToken: null, user: null, isAuthenticated: false }),
    }),
    { name: 'razorpay-recovery-auth' }
  )
)
