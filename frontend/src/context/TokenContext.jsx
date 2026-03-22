import { createContext, useContext, useState } from 'react';

const TokenContext = createContext(null);

// Access token is held in useState — JavaScript memory only.
// Never written to localStorage, sessionStorage, or cookies (INV-02).
export function TokenProvider({ children }) {
  const [accessToken, setAccessToken] = useState(null);

  return (
    <TokenContext.Provider value={{ accessToken, setAccessToken }}>
      {children}
    </TokenContext.Provider>
  );
}

export function useToken() {
  const ctx = useContext(TokenContext);
  if (!ctx) throw new Error('useToken must be used within a TokenProvider');
  return ctx;
}
