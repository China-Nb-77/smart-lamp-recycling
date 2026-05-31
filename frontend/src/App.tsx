import { Outlet } from 'react-router-dom';

export function App() {
  return (
    <div className="app-stage">
      <div className="app-frame">
        <Outlet />
      </div>
    </div>
  );
}
