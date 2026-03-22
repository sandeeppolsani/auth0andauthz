import { useState } from 'react';
import { useToken } from '../context/TokenContext';

const API_A = 'http://localhost:3001';
const API_B = 'http://localhost:3002';

const POST_USER_BODY = { email: 'test@example.com', name: 'Test', department: 'QA', employee_number: 'EMP999' };
const PUT_USER_BODY = { department: 'Updated' };
const POST_CONFIG_BODY = { log_level: 'DEBUG' };

function getStatusStyle(status) {
  if (status === 200) return { border: '2px solid green', color: 'green' };
  if (status === 401) return { border: '2px solid red', color: 'red' };
  if (status === 403) return { border: '2px solid orange', color: 'orange' };
  if (status >= 400) return { border: '2px solid red', color: 'red' };
  if (status === 0) return { border: '2px solid gray', color: 'gray' };
  return { border: '2px solid green', color: 'green' };
}

function getStatusLabel(status) {
  if (status === 401) return 'Unauthenticated';
  if (status === 403) return 'Forbidden';
  return null;
}

function ResponseBlock({ response, truncatedToken }) {
  if (!response) return null;
  const style = getStatusStyle(response.status);
  const label = getStatusLabel(response.status);

  return (
    <div style={{ marginTop: '0.5rem', padding: '0.5rem', ...style }}>
      <div style={{ fontFamily: 'monospace', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
        <div>{response.method} {response.url}</div>
        <div>Authorization: Bearer {truncatedToken}</div>
      </div>
      <div>
        <strong style={{ fontSize: '1.4rem', ...style }}>{response.status}</strong>
        {label && <span style={{ marginLeft: '0.5rem', fontWeight: 'bold' }}>{label}</span>}
      </div>
      <pre style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.85rem' }}>
        {response.body}
      </pre>
    </div>
  );
}

export default function ApiTester() {
  const { accessToken } = useToken();
  const [responses, setResponses] = useState({});
  const [idInputs, setIdInputs] = useState({ getUserEmail: '', putUserEmail: '' });

  const setResponse = (id, data) =>
    setResponses(prev => ({ ...prev, [id]: data }));

  const call = async (id, method, url, body) => {
    if (!accessToken) return;

    const headers = {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    };

    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    try {
      const res = await fetch(url, options);
      let displayBody;
      try {
        const json = await res.json();
        displayBody = JSON.stringify(json, null, 2);
      } catch {
        displayBody = await res.text();
      }
      setResponse(id, { method, url, status: res.status, body: displayBody });
    } catch (err) {
      setResponse(id, { method, url, status: 0, body: `Network error: ${err.message}` });
    }
  };

  if (!accessToken) {
    return <div><strong>Login required</strong> — no access token in context.</div>;
  }

  const truncatedToken = `${accessToken.slice(0, 20)}...`;

  return (
    <div>
      <h2>API Tester</h2>

      <h3>API A — {API_A}</h3>

      {/* GET /api/users */}
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={() => call('get-users', 'GET', `${API_A}/api/users`)}>
          GET /api/users
        </button>
        <ResponseBlock response={responses['get-users']} truncatedToken={truncatedToken} />
      </div>

      {/* GET /api/users/:id */}
      <div style={{ marginBottom: '1rem' }}>
        <input
          type="text"
          placeholder="email (e.g. alice@example.com)"
          value={idInputs.getUserEmail}
          onChange={e => setIdInputs(prev => ({ ...prev, getUserEmail: e.target.value }))}
          style={{ marginRight: '0.5rem', width: '240px' }}
        />
        <button
          onClick={() => call('get-user', 'GET', `${API_A}/api/users/${encodeURIComponent(idInputs.getUserEmail)}`)}
          disabled={!idInputs.getUserEmail}
        >
          GET /api/users/:id
        </button>
        <ResponseBlock response={responses['get-user']} truncatedToken={truncatedToken} />
      </div>

      {/* POST /api/users */}
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={() => call('post-user', 'POST', `${API_A}/api/users`, POST_USER_BODY)}>
          POST /api/users
        </button>
        <ResponseBlock response={responses['post-user']} truncatedToken={truncatedToken} />
      </div>

      {/* PUT /api/users/:id */}
      <div style={{ marginBottom: '1rem' }}>
        <input
          type="text"
          placeholder="email (e.g. alice@example.com)"
          value={idInputs.putUserEmail}
          onChange={e => setIdInputs(prev => ({ ...prev, putUserEmail: e.target.value }))}
          style={{ marginRight: '0.5rem', width: '240px' }}
        />
        <button
          onClick={() => call('put-user', 'PUT', `${API_A}/api/users/${encodeURIComponent(idInputs.putUserEmail)}`, PUT_USER_BODY)}
          disabled={!idInputs.putUserEmail}
        >
          PUT /api/users/:id
        </button>
        <ResponseBlock response={responses['put-user']} truncatedToken={truncatedToken} />
      </div>

      <h3>API B — {API_B}</h3>

      {/* GET /api/analytics/summary */}
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={() => call('analytics', 'GET', `${API_B}/api/analytics/summary`)}>
          GET /api/analytics/summary
        </button>
        <ResponseBlock response={responses['analytics']} truncatedToken={truncatedToken} />
      </div>

      {/* GET /api/config */}
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={() => call('get-config', 'GET', `${API_B}/api/config`)}>
          GET /api/config
        </button>
        <ResponseBlock response={responses['get-config']} truncatedToken={truncatedToken} />
      </div>

      {/* POST /api/config */}
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={() => call('post-config', 'POST', `${API_B}/api/config`, POST_CONFIG_BODY)}>
          POST /api/config
        </button>
        <ResponseBlock response={responses['post-config']} truncatedToken={truncatedToken} />
      </div>

      {/* GET /api/audit-log */}
      <div style={{ marginBottom: '1rem' }}>
        <button onClick={() => call('audit-log', 'GET', `${API_B}/api/audit-log`)}>
          GET /api/audit-log
        </button>
        <ResponseBlock response={responses['audit-log']} truncatedToken={truncatedToken} />
      </div>
    </div>
  );
}
