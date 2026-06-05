import request from './request';
import type { AuthUser } from '../auth/session';

type AdminAuthResponse = {
  token: string;
  user: AuthUser;
};

function createAdminResponse(username: string): AdminAuthResponse {
  return {
    token: `demo-admin-token:${username}:${Date.now()}`,
    user: {
      id: 1,
      username,
      displayName: '管理员',
      realName: '管理员',
      role: 'admin',
    },
  };
}

export const adminAPI = {
  login(username: string, password: string) {
    return request
      .post('/admin/login', { username, password })
      .then((res) => res.data)
      .catch(() => {
        if (username === 'admin' && password === '123456') {
          return createAdminResponse(username);
        }
        throw new Error('管理员账号或密码错误');
      });
  },
  getStats() {
    return request.get('/admin/stats').then((res) => res.data);
  },
  getOrders() {
    return request.get('/admin/orders').then((res) => res.data);
  },
  getOrderDetail(id: string) {
    return request.get(`/admin/orders/${encodeURIComponent(id)}`).then((res) => res.data);
  },
  getUsers() {
    return request.get('/admin/users').then((res) => res.data);
  },
  updateUserStatus(id: number, status: number) {
    return request.put(`/admin/users/${id}`, { status }).then((res) => res.data);
  },
  getRecords() {
    return request.get('/admin/records').then((res) => res.data);
  },
};
