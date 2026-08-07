import axios from "axios";

export const API_ORIGIN = import.meta.env.VITE_API_URL || "http://localhost:5050";

const api = axios.create({
  baseURL: `${API_ORIGIN}/api`,
  headers: { "Content-Type": "application/json" },
});

export default api;
