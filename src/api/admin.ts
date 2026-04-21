import request from './request';

export const adminAPI = {
  login(username: string, password: string) {
    return request.post('/admin/login', { username, password }).then((res) => res.data);
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
