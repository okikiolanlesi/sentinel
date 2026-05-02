import axios from "axios";

// Base URL points at the backend root. Service files use full paths like '/api/auth/login'.
// In production set VITE_API_URL=https://your-deployed-backend.com
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

http.interceptors.request.use((config) => {
  try {
    const persisted = localStorage.getItem('sentinel-auth')
    const token = persisted
      ? (JSON.parse(persisted) as { state?: { token?: string } }).state?.token
      : null
    if (token) config.headers.Authorization = `Bearer ${token}`
  } catch {
    // ignore parse errors
  }
  return config;
});

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      // Don't redirect if user is already on an auth page (avoids loops on bad-login)
      const path = window.location.pathname
      if (!path.startsWith('/sign-in') && !path.startsWith('/sign-up')) {
        localStorage.removeItem('sentinel-auth')
        window.location.href = '/sign-in'
      }
    }
    return Promise.reject(err);
  },
);
