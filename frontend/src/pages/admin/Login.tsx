import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminAPI } from '../../api/admin';
import { setAdminSession } from '../../auth/session';
import { ErrorState } from '../../components/feedback/ErrorState';

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('123456');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const payload = await adminAPI.login(username, password);
      setAdminSession(payload.token, payload.user);
      navigate('/admin/dashboard');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '管理员登录失败');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="payment-card auth-card">
        <div className="payment-card__header">
          <div>
            <strong>管理员登录</strong>
            <p>登录后台查看订单、用户与回收记录</p>
          </div>
        </div>
        {error ? <ErrorState title="登录失败" description={error} /> : null}
        <form className="payment-form auth-form" onSubmit={handleSubmit}>
          <label>
            <span>用户名</span>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label>
            <span>密码</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button type="submit" className="primary-button payment-form__submit" disabled={submitting}>
            {submitting ? '登录中...' : '进入后台'}
          </button>
        </form>
      </section>
    </main>
  );
}
