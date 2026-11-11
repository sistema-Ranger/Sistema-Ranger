const API = `${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1`;
const KEY = "ranger_token";

export const token = {
  get: () => localStorage.getItem(KEY),
  set: (t) => localStorage.setItem(KEY, t),
  clear: () => localStorage.removeItem(KEY),
};

export class ApiError extends Error {
  constructor(status, message, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// El backend responde {detail, code}; en 422 `detail` es una lista de Pydantic.
const toText = (d) => (Array.isArray(d) ? d.map((x) => x.msg).join(". ") : d);

async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const t = token.get();
  if (t) headers.Authorization = `Bearer ${t}`;
  let payload;
  if (form) payload = new URLSearchParams(form);
  else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(`${API}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor. Revisa que el backend esté activo.", "NETWORK");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && t) {
      token.clear();
      window.dispatchEvent(new Event("ranger:logout"));
    }
    throw new ApiError(res.status, toText(data.detail) ?? "Error inesperado", data.code);
  }
  return data;
}

export const api = {
  login: (email, password) => request("/auth/login", { method: "POST", form: { username: email, password } }),
  me: () => request("/auth/me"),
  users: {
    list: (page = 1, size = 50) => request(`/users?page=${page}&size=${size}`),
    create: (body) => request("/users", { method: "POST", body }),
    update: (id, body) => request(`/users/${id}`, { method: "PATCH", body }),
    deactivate: (id) => request(`/users/${id}`, { method: "DELETE" }),
  },
};
