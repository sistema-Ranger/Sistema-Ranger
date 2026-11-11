import { createContext, useContext, useEffect, useState } from "react";
import { api, token } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!token.get());

  useEffect(() => {
    if (!token.get()) return;
    api.me().then(setUser).catch(() => token.clear()).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const out = () => setUser(null);
    window.addEventListener("ranger:logout", out);
    return () => window.removeEventListener("ranger:logout", out);
  }, []);

  const login = async (email, password) => {
    const r = await api.login(email, password);
    token.set(r.access_token);
    setUser(r.user);
  };
  const logout = () => {
    token.clear();
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>;
}
