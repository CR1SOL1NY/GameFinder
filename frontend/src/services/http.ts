export class ApiError extends Error { constructor(public status: number, message: string) { super(message); } }
const base = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');
let onExpired = () => {};
export const setSessionExpiredHandler = (fn: () => void) => { onExpired = fn; };
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(15000);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, { ...init, signal, credentials: 'include', headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers } });
  } catch (err) {
    if (init.signal?.aborted) throw err;
    throw new ApiError(0, 'No pudimos conectar con GameFinder. Revisa tu conexión e intenta nuevamente.');
  }
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    let detail = `No pudimos completar la solicitud (HTTP ${response.status}).`;
    if (data && typeof data === 'object' && 'detail' in data) {
      const d = (data as { detail: unknown }).detail;
      if (typeof d === 'string') detail = d;
      if (Array.isArray(d)) detail = d.map(v => typeof v?.msg === 'string' ? v.msg : 'Revisa los campos del formulario.').join(' · ');
    }
    if (response.status === 401 && path !== '/usuarios/login' && path !== '/usuarios/me') onExpired();
    if (response.status === 429) detail = 'Has realizado muchos intentos. Espera un minuto y vuelve a intentar.';
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  try { return await response.json() as T; }
  catch { throw new ApiError(response.status, 'El servidor devolvió una respuesta que no pudimos interpretar. Intenta nuevamente.'); }
}
export const jsonBody = (method: string, data: unknown): RequestInit => ({ method, body: JSON.stringify(data) });
export const errorMessage = (e: unknown) => e instanceof Error ? e.message : 'No pudimos completar la operación.';
