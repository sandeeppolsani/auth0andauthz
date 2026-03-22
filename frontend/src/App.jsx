import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { Security, LoginCallback, SecureRoute } from '@okta/okta-react';
import { toRelativeUrl } from '@okta/okta-auth-js';
import { oktaAuth } from './config/oktaConfig';

function LoginPage() {
  return <div>Login Page</div>;
}

function Dashboard() {
  return <div>Dashboard</div>;
}

function AppRoutes() {
  const navigate = useNavigate();

  const restoreOriginalUri = (_oktaAuth, originalUri) => {
    navigate(toRelativeUrl(originalUri || '/', window.location.origin), { replace: true });
  };

  return (
    <Security oktaAuth={oktaAuth} restoreOriginalUri={restoreOriginalUri}>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/login/callback" element={<LoginCallback />} />
        <Route
          path="/dashboard"
          element={
            <SecureRoute>
              <Dashboard />
            </SecureRoute>
          }
        />
      </Routes>
    </Security>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
