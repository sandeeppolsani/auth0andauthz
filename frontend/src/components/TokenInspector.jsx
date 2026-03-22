import { useState, useEffect } from 'react';
import { useToken } from '../context/TokenContext';

const KNOWN_CLAIMS = ['iss', 'sub', 'aud', 'exp', 'iat', 'scp', 'groups', 'department', 'employee_id'];

function decodeSegment(segment) {
  const padded = segment.replace(/-/g, '+').replace(/_/g, '/');
  const padLength = (4 - padded.length % 4) % 4;
  return JSON.parse(atob(padded + '='.repeat(padLength)));
}

export default function TokenInspector() {
  const { accessToken } = useToken();
  const [countdown, setCountdown] = useState(null);

  let header = null;
  let payload = null;
  let segments = null;
  let parseError = false;

  if (accessToken) {
    try {
      const parts = accessToken.split('.');
      if (parts.length !== 3) throw new Error('Invalid JWT format');
      segments = parts;
      header = decodeSegment(parts[0]);
      payload = decodeSegment(parts[1]);
    } catch {
      parseError = true;
    }
  }

  const exp = payload?.exp;

  useEffect(() => {
    if (!exp) return;

    const tick = () => setCountdown(Math.floor(exp - Date.now() / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [exp]);

  if (!accessToken) {
    return <div>No access token — please log in.</div>;
  }

  if (parseError) {
    return <div>Token decode error.</div>;
  }

  const scopes = Array.isArray(payload.scp)
    ? payload.scp
    : (payload.scp ?? '').split(' ').filter(Boolean);

  const groups = payload.groups ?? [];

  const extraClaims = Object.entries(payload).filter(([k]) => !KNOWN_CLAIMS.includes(k));

  return (
    <div>
      <h2>Token Inspector</h2>

      <section>
        <h3>Header</h3>
        <p><strong>alg:</strong> {header.alg}</p>
        <p><strong>kid:</strong> {header.kid}</p>
      </section>

      <section>
        <h3>Payload</h3>
        <p><strong>iss:</strong> {payload.iss}</p>
        <p><strong>sub:</strong> {payload.sub}</p>
        <p><strong>aud:</strong> {Array.isArray(payload.aud) ? payload.aud.join(', ') : payload.aud}</p>
        <p><strong>exp:</strong> {payload.exp}</p>
        <p><strong>iat:</strong> {payload.iat}</p>
        <div>
          <strong>scp:</strong>
          <ul>{scopes.map(s => <li key={s}>{s}</li>)}</ul>
        </div>
        <div>
          <strong>groups:</strong>
          <ul>{groups.length > 0 ? groups.map(g => <li key={g}>{g}</li>) : <li>—</li>}</ul>
        </div>
        <p><strong>department:</strong> {payload.department ?? '—'}</p>
        <p><strong>employee_id:</strong> {payload.employee_id ?? '—'}</p>
        {extraClaims.map(([k, v]) => (
          <p key={k}>
            <strong>{k}:</strong> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
          </p>
        ))}
      </section>

      <section>
        <h3>Expiry</h3>
        <p style={{ color: countdown !== null && countdown < 60 ? 'red' : 'inherit' }}>
          {countdown === null ? '...' : countdown > 0 ? `Expires in ${countdown}s` : 'Expired'}
        </p>
      </section>

      <section>
        <h3>Raw Segments</h3>
        <p><strong>Header:</strong></p>
        <pre style={{ wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>{segments[0]}</pre>
        <p><strong>Payload:</strong></p>
        <pre style={{ wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>{segments[1]}</pre>
        <p><strong>Signature:</strong></p>
        <pre style={{ wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>{segments[2]}</pre>
      </section>
    </div>
  );
}
