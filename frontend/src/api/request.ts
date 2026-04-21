import axios from 'axios';
import {
  clearAdminSession,
  clearUserSession,
  getStoredUser,
  getAdminToken,
  getUserRefreshToken,
  getUserToken,
  setUserSession,
} from '../auth/session';
import { legacyApiBaseUrl, resolveRequestUrl } from '../services/api/base-url';

const request = axios.create({
  baseURL: legacyApiBaseUrl,
  timeout: 15000,
});

let refreshingPromise: Promise<string> | null = null;

async function refreshUserToken() {
  const token = getUserToken();
  if (token.startsWith('demo-token:')) {
    return token;
  }
  if (!refreshingPromise) {
    refreshingPromise = axios
      .post(resolveRequestUrl(legacyApiBaseUrl, '/auth/refresh'), {
        refresh_token: getUserRefreshToken(),
      })
      .then((response) => {
        const data = response.data || {};
        setUserSession(data.token || '', data.refresh_token || '', data.user || {});
        return data.token || '';
      })
      .finally(() => {
        refreshingPromise = null;
      });
  }
  return refreshingPromise;
}

request.interceptors.request.use((config) => {
  const url = config.url || '';
  const isAdmin = url.startsWith('/admin');
  const token = isAdmin ? getAdminToken() : getUserToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const url = String(error?.config?.url || '');
    const isAdmin = url.startsWith('/admin');

    if (status === 401 && !isAdmin && !url.startsWith('/auth/')) {
      if (getUserToken().startsWith('demo-token:') && getStoredUser()) {
        return Promise.reject(error);
      }
      try {
        const nextToken = await refreshUserToken();
        if (nextToken) {
          error.config.headers = error.config.headers || {};
          error.config.headers.Authorization = `Bearer ${nextToken}`;
          return request(error.config);
        }
      } catch {
        clearUserSession();
        window.location.href = '/login';
        return Promise.reject(error);
      }
    }

    if (status === 401 && isAdmin) {
      clearAdminSession();
      window.location.href = '/admin/login';
    }

    if (status === 401 && !isAdmin && url.startsWith('/auth/')) {
      if (getUserToken().startsWith('demo-token:') && getStoredUser()) {
        return Promise.reject(error);
      }
      clearUserSession();
      window.location.href = '/login';
    }

    return Promise.reject(error);
  },
);

export default request;
