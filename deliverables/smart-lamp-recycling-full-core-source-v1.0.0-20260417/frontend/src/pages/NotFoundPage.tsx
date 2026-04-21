import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <main className="page-shell">
      <section className="feedback-card feedback-card--error">
        <div className="feedback-card__icon">404</div>
        <h1>页面不存在</h1>
        <p>当前地址没有对应页面，请返回智能体首页继续操作。</p>
        <Link className="secondary-button" to="/">
          返回首页
        </Link>
      </section>
    </main>
  );
}
