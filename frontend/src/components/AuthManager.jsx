import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOktaAuth } from '@okta/okta-react';
import { useToken } from '../context/TokenContext';

function decodeExp(token) {
  try {
    const segment = token.split('.')[1];
    const padded = segment.replace(/-/g, '+').replace(/_/g, '/');
    const padLength = (4 - padded.length % 4) % 4;
    return JSON.parse(atob(padded + '='.repeat(padLength))).exp;
  } catch {
    return null;
  }
}

// Renders null. Mounted once inside <Security>, outside <Routes>.
// Proactive refresh timer: fires 60s before exp, resets after each renewal (INV-05).
export default function AuthManager() {
  const { accessToken, setAccessToken } = useToken();
  const { oktaAuth } = useOktaAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!accessToken) return;

    const exp = decodeExp(accessToken);
    if (!exp) return;

    const refreshAt = (exp * 1000) - Date.now() - 60000;
    if (refreshAt <= 0) return;

    const id = setTimeout(async () => {
      try {
        await oktaAuth.tokenManager.renew('accessToken');
        const newToken = oktaAuth.getAccessToken();
        setAccessToken(newToken);
        // setAccessToken triggers accessToken change → useEffect re-runs → timer rescheduled (INV-05)
      } catch {
        // INV-06: refresh failure → clear token, redirect to login
        setAccessToken(null);
        navigate('/', { replace: true });
      }
    }, refreshAt);

    // Cleanup: clears timer on unmount AND on every accessToken change,
    // ensuring the previous timer is always cancelled before the next is set (INV-05)
    return () => clearTimeout(id);
  }, [accessToken, oktaAuth, setAccessToken, navigate]);

  return null;
}
