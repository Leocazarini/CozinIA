import { QueryClient } from '@tanstack/react-query'

// Single shared instance mounted once at the App root.
export const queryClient = new QueryClient()
