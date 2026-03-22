import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useOktaAuth } from '@okta/okta-react';
import { useToken } from '../context/TokenContext';

export default function Dashboard() {
  const { authState, oktaAuth } = useOktaAuth();
  const { accessToken, setAccessToken } = useToken();
  const navigate = useNavigate();

  useEffect(() => {
    if (!authState?.isAuthenticated) return;

    const token = oktaAuth.getAccessToken();
    if (token) {
      setAccessToken(token);
    } else {
      // Token missing or expired — session cannot continue (INV-06)
      oktaAuth.signOut().then(() => navigate('/', { replace: true }));
    }
  }, [authState, oktaAuth, setAccessToken, navigate]);

  const claims = authState?.idToken?.claims;

  return (
    <div>
      <h1>Dashboard</h1>
      <p><strong>Name:</strong> {claims?.name}</p>
      <p><strong>Email:</strong> {claims?.email}</p>
      <p><strong>Token:</strong> {accessToken ? 'Token loaded' : 'No token'}</p>
      <nav>
        <Link to="/token-inspector">Token Inspector</Link>
        {' | '}
        <Link to="/api-tester">API Tester</Link>
        {' | '}
        <Link to="/token-refresh">Token Refresh Demo</Link>
      </nav>
    </div>
  );
}
