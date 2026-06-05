import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_PROXY_TARGET || 'http://192.168.200.51:8080';
  const paymentTarget = env.VITE_PAYMENT_PROXY_TARGET || 'http://192.168.200.51:8081';
  const songTarget = env.VITE_SONG_PROXY_TARGET || apiTarget;
  const visionTarget = env.VITE_VISION_PROXY_TARGET || 'http://127.0.0.1:8000';

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api/recommend': {
          target: visionTarget,
          changeOrigin: true,
        },
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/pay-api': {
          target: paymentTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/pay-api/, ''),
        },
        '/song-api': {
          target: songTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/song-api/, ''),
        },
        '/vision-api': {
          target: visionTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/vision-api/, ''),
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: 4173,
    },
  };
});
