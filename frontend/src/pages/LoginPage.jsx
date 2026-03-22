import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOktaAuth } from '@okta/okta-react';
import { oktaAuth } from '../config/oktaConfig';

const SCOPES = ['openid', 'profile', 'email', 'offline_access', 'api-a:read', 'api-a:write', 'api-b:read', 'api-b:admin'];

export default function LoginPage() {
  const { authState } = useOktaAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (authState?.isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [authState, navigate]);

  const handleLogin = () => {
    oktaAuth.signInWithRedirect({ scopes: SCOPES });
  };

  return (
    <div>
      <button onClick={handleLogin}>Login with Okta</button>
    </div>
  );
}
