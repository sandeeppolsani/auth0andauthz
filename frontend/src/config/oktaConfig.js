import { OktaAuth } from '@okta/okta-auth-js';

export const oktaAuth = new OktaAuth({
  issuer: import.meta.env.VITE_OKTA_ISSUER,
  clientId: import.meta.env.VITE_OKTA_CLIENT_ID,
  redirectUri: import.meta.env.VITE_OKTA_REDIRECT_URI,
  scopes: ['openid', 'profile', 'email', 'offline_access', 'api-a:read', 'api-a:write', 'api-b:read', 'api-b:admin'],
  pkce: true,
  tokenManager: {
    storage: 'sessionStorage',   // refresh tokens only — NOT access tokens
    storageKey: 'okta-token-storage',
  },
});

// CRITICAL: Access tokens must NOT be stored by the SDK in localStorage.
// The tokenManager stores tokens — access tokens are stored in session-scoped memory,
// refresh tokens use sessionStorage. Verify the SDK default behaviour satisfies INV-02 and INV-03.
