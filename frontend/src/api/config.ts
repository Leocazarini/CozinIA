// Base URL of the backend API. Overridable via VITE_API_URL (see
// docker-compose.yml); defaults to the backend's published dev port.
export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
