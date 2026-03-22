import { useState } from 'react';
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

function TokenPanel({ label, token, otherExp }) {
  const exp = token ? decodeExp(token) : null;
  const renewed = exp !== null && otherExp !== null && exp > otherExp;

  return (
    <div style={{ flex: 1, border: '1px solid #ccc', padding: '1rem' }}>
      <h3>{label}</h3>
      {token ? (
        <div>
          <p><strong>exp:</strong> {exp}</p>
          <p><strong>Expires at:</strong> {exp ? new Date(exp * 1000).toISOString() : '—'}</p>
          {renewed && (
            <p style={{ color: 'green' }}>
              Token renewed — exp is {exp - otherExp}s later
            </p>
          )}
        </div>
      ) : (
        <p style={{ color: '#888' }}>{label === 'After' ? 'Waiting...' : 'No token'}</p>
      )}
    </div>
  );
}

export default function TokenRefreshDemo() {
  const { accessToken, setAccessToken } = useToken();
  const { oktaAuth } = useOktaAuth();
  const navigate = useNavigate();

  const [beforeToken, setBeforeToken] = useState(null);
  const [afterToken, setAfterToken] = useState(null);
  const [refreshStatus, setRefreshStatus] = useState('idle');

  const handleRefresh = async () => {
    // INV-26: snapshot before state BEFORE calling renew — never overwritten on success
    setBeforeToken(accessToken);
    setRefreshStatus('refreshing');

    try {
      await oktaAuth.tokenManager.renew('accessToken');
      const newToken = oktaAuth.getAccessToken();
      setAfterToken(newToken);
      setAccessToken(newToken);
      setRefreshStatus('success');
    } catch {
      setRefreshStatus('error');
      // INV-06: refresh failure → clear session and redirect to login
      oktaAuth.signOut().then(() => navigate('/', { replace: true }));
    }
  };

  const beforeExp = beforeToken ? decodeExp(beforeToken) : null;

  return (
    <div>
      <h2>Token Refresh Demo</h2>

      <button
        onClick={handleRefresh}
        disabled={!accessToken || refreshStatus === 'refreshing'}
      >
        {refreshStatus === 'refreshing' ? 'Refreshing...' : 'Trigger Silent Refresh'}
      </button>

      {refreshStatus === 'error' && (
        <p style={{ color: 'red' }}>Refresh failed — redirecting to login...</p>
      )}

      <div style={{ display: 'flex', gap: '2rem', marginTop: '1rem' }}>
        <TokenPanel label="Before" token={beforeToken} otherExp={null} />
        <TokenPanel label="After" token={afterToken} otherExp={beforeExp} />
      </div>
    </div>
  );
}
