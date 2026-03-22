import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { Security, LoginCallback, useOktaAuth } from '@okta/okta-react';
import { toRelativeUrl } from '@okta/okta-auth-js';
import { oktaAuth } from './config/oktaConfig';
import { TokenProvider } from './context/TokenContext';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import TokenInspector from './components/TokenInspector';
import ApiTester from './components/ApiTester';
import TokenRefreshDemo from './components/TokenRefreshDemo';
import AuthManager from './components/AuthManager';

// SecureRoute from @okta/okta-react v6 uses useRouteMatch (react-router-dom v5 API).
// Custom implementation using useOktaAuth + useEffect for v6/v7 compatibility.
function SecureRoute({ children }) {
  const { oktaAuth: auth, authState } = useOktaAuth();

  useEffect(() => {
    if (!authState) return;
    if (!authState.isAuthenticated) {
      const originalUri = toRelativeUrl(window.location.href, window.location.origin);
      auth.setOriginalUri(originalUri);
      auth.signInWithRedirect();
    }
  }, [authState, auth]);

  if (!authState || !authState.isAuthenticated) {
    return null;
  }

  return children;
}

function AppRoutes() {
  const navigate = useNavigate();

  const restoreOriginalUri = (_oktaAuth, originalUri) => {
    navigate(toRelativeUrl(originalUri || '/', window.location.origin), { replace: true });
  };

  return (
    <Security oktaAuth={oktaAuth} restoreOriginalUri={restoreOriginalUri}>
      <AuthManager />
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
        <Route
          path="/token-inspector"
          element={
            <SecureRoute>
              <TokenInspector />
            </SecureRoute>
          }
        />
        <Route
          path="/api-tester"
          element={
            <SecureRoute>
              <ApiTester />
            </SecureRoute>
          }
        />
        <Route
          path="/token-refresh"
          element={
            <SecureRoute>
              <TokenRefreshDemo />
            </SecureRoute>
          }
        />
      </Routes>
    </Security>
  );
}

export default function App() {
  return (
    <TokenProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </TokenProvider>
  );
}
