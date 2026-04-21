import { createBrowserRouter } from 'react-router-dom';
import { App } from '../App';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AdminProtectedRoute } from '../components/AdminProtectedRoute';
import { AdminLayout } from '../components/admin/AdminLayout';
import { ChatPage } from '../pages/ChatPage';
import { ElectronicOrderPage } from '../pages/ElectronicOrderPage';
import { QrErrorPage } from '../pages/QrErrorPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { ProfilePage } from '../pages/ProfilePage';
import { PaymentOrderCreatePage } from '../pages/payment/PaymentOrderCreatePage';
import { PaymentOrderDetailPage } from '../pages/payment/PaymentOrderDetailPage';
import { PaymentProcessPage } from '../pages/payment/PaymentProcessPage';
import { PaymentSuccessPage } from '../pages/payment/PaymentSuccessPage';
import { PaymentFailurePage } from '../pages/payment/PaymentFailurePage';
import { AdminLoginPage } from '../pages/admin/Login';
import { AdminDashboardPage } from '../pages/admin/Dashboard';
import { AdminOrdersPage } from '../pages/admin/Orders';
import { AdminOrderDetailPage } from '../pages/admin/OrderDetail';
import { AdminUsersPage } from '../pages/admin/Users';
import { AdminRecordsPage } from '../pages/admin/Records';

export const router = createBrowserRouter([
  {
    path: '/admin/login',
    element: <AdminLoginPage />,
  },
  {
    path: '/admin',
    element: (
      <AdminProtectedRoute>
        <AdminLayout />
      </AdminProtectedRoute>
    ),
    children: [
      {
        path: 'dashboard',
        element: <AdminDashboardPage />,
      },
      {
        path: 'orders',
        element: <AdminOrdersPage />,
      },
      {
        path: 'orders/:id',
        element: <AdminOrderDetailPage />,
      },
      {
        path: 'users',
        element: <AdminUsersPage />,
      },
      {
        path: 'records',
        element: <AdminRecordsPage />,
      },
    ],
  },
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: (
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'login',
        element: <LoginPage />,
      },
      {
        path: 'register',
        element: <RegisterPage />,
      },
      {
        path: 'profile',
        element: (
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'order/:orderId/electronic',
        element: (
          <ProtectedRoute>
            <ElectronicOrderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'qr/error',
        element: <QrErrorPage />,
      },
      {
        path: 'payment/orders/new',
        element: (
          <ProtectedRoute>
            <PaymentOrderCreatePage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'payment/orders/:orderId',
        element: (
          <ProtectedRoute>
            <PaymentOrderDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'payment/orders/:orderId/pay',
        element: (
          <ProtectedRoute>
            <PaymentProcessPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'payment/orders/:orderId/pay/success',
        element: (
          <ProtectedRoute>
            <PaymentSuccessPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'payment/orders/:orderId/pay/failure',
        element: (
          <ProtectedRoute>
            <PaymentFailurePage />
          </ProtectedRoute>
        ),
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
]);
