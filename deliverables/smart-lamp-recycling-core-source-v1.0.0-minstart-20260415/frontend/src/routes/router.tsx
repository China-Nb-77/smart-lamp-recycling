import { createBrowserRouter } from 'react-router-dom';
import { App } from '../App';
import { ChatPage } from '../pages/ChatPage';
import { ElectronicOrderPage } from '../pages/ElectronicOrderPage';
import { QrErrorPage } from '../pages/QrErrorPage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { PaymentOrderCreatePage } from '../pages/payment/PaymentOrderCreatePage';
import { PaymentOrderDetailPage } from '../pages/payment/PaymentOrderDetailPage';
import { PaymentProcessPage } from '../pages/payment/PaymentProcessPage';
import { PaymentSuccessPage } from '../pages/payment/PaymentSuccessPage';
import { PaymentFailurePage } from '../pages/payment/PaymentFailurePage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <ChatPage />,
      },
      {
        path: 'order/:orderId/electronic',
        element: <ElectronicOrderPage />,
      },
      {
        path: 'qr/error',
        element: <QrErrorPage />,
      },
      {
        path: 'payment/orders/new',
        element: <PaymentOrderCreatePage />,
      },
      {
        path: 'payment/orders/:orderId',
        element: <PaymentOrderDetailPage />,
      },
      {
        path: 'payment/orders/:orderId/pay',
        element: <PaymentProcessPage />,
      },
      {
        path: 'payment/orders/:orderId/pay/success',
        element: <PaymentSuccessPage />,
      },
      {
        path: 'payment/orders/:orderId/pay/failure',
        element: <PaymentFailurePage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
]);
