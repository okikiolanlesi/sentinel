import axios from "axios";

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

http.interceptors.request.use((config) => {
  try {
    const persisted = localStorage.getItem("sentinel-auth");
    const token = persisted
      ? (JSON.parse(persisted) as { state?: { token?: string } }).state?.token
      : null;
    if (token) config.headers.Authorization = `Bearer ${token}`;
  } catch {
    // ignore parse errors
  }
  return config;
});

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      localStorage.removeItem("sentinel-auth");
      window.location.href = "/sign-in";
    }
    return Promise.reject(err);
  },
);
