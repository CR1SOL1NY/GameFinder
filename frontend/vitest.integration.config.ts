import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],test:{environment:'jsdom',setupFiles:['./tests/setup.ts'],include:['tests/integration/**/*.test.tsx'],env:{VITE_API_URL:'http://127.0.0.1:8017/interfaz'},testTimeout:30000,environmentOptions:{jsdom:{url:'http://localhost:5173'}}}});
