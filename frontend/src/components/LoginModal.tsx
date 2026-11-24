import { useEffect, useRef, useState } from 'react';
import { iniciarSesion, registrarUsuario, type Usuario } from '../authApi';
import { errorMessage } from '../services/http';
import { Icon, fieldCls } from './common';
export default function LoginModal({reason, onConfirm, onClose}: {reason: string; onConfirm: (user: Usuario) => void; onClose: () => void}) {
  const [mode, setMode] = useState<'login'|'register'>('login');
  const [nombre,setNombre] = useState(''), [correo,setCorreo] = useState(''), [contrasena,setContrasena] = useState('');
  const [error,setError] = useState(''), [busy,setBusy] = useState(false);
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    dialog.current?.querySelector<HTMLInputElement>('input')?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onClose();
      if (e.key === 'Tab') {
        const nodes = dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled)');
        if (!nodes?.length) return;
        const first=nodes[0], last=nodes[nodes.length-1];
        if (e.shiftKey && document.activeElement===first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement===last) { e.preventDefault(); first.focus(); }
      }
    };
    const oldOverflow=document.body.style.overflow; document.body.style.overflow='hidden';
    window.addEventListener('keydown',key);
    return () => {window.removeEventListener('keydown',key);document.body.style.overflow=oldOverflow;before?.focus();};
  }, [onClose,busy]);
  async function submit(e: React.FormEvent) {
    e.preventDefault();setError('');
    if(mode==='register' && new TextEncoder().encode(contrasena).length>72) return setError('La contraseña admite hasta 72 bytes UTF-8.');
    setBusy(true);
    try { onConfirm(mode==='login' ? await iniciarSesion(correo,contrasena) : await registrarUsuario(nombre,correo,contrasena)); }
    catch(e) {setError(errorMessage(e));} finally {setBusy(false);}
  }
  return <div className="fixed inset-0 z-[80] grid place-items-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)onClose();}}>
    <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="auth-title" className="w-full max-w-sm rounded-2xl border border-blue-500/30 bg-panel p-6 shadow-2xl">
      <Icon name="lock" className="mx-auto size-10 text-blue-400"/><h2 id="auth-title" className="mt-4 text-center text-xl font-extrabold">{mode==='login'?'Iniciar sesión':'Crear cuenta'}</h2><p className="mt-2 text-center text-sm text-slate-400">{reason}</p>
      <form onSubmit={submit} className="mt-5 space-y-4">
        {mode==='register'&&<label className="block text-sm">Nombre<input autoComplete="name" required minLength={2} maxLength={80} value={nombre} onChange={e=>setNombre(e.target.value)} className={fieldCls}/></label>}
        <label className="block text-sm">Correo electrónico<input type="email" autoComplete="email" required value={correo} onChange={e=>setCorreo(e.target.value)} className={fieldCls}/></label>
        <label className="block text-sm">Contraseña<input type="password" autoComplete={mode==='login'?'current-password':'new-password'} required minLength={mode==='register'?8:1} maxLength={mode==='register'?72:256} value={contrasena} onChange={e=>setContrasena(e.target.value)} className={fieldCls}/></label>
        {mode==='register'&&<p className="text-xs text-slate-400">Usa al menos 8 caracteres. El correo debe tener un formato válido.</p>}
        {error&&<p role="alert" className="text-sm text-rose-300">{error}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-blue-600 py-3 text-sm font-bold text-white disabled:opacity-50">{busy?'Procesando…':mode==='login'?'Iniciar sesión':'Crear cuenta'}</button>
      </form>
      <button disabled={busy} onClick={()=>{setMode(mode==='login'?'register':'login');setError('');}} className="mt-3 w-full rounded-lg border border-blue-500/30 py-3 text-sm">{mode==='login'?'¿No tienes cuenta? Regístrate':'Ya tengo una cuenta'}</button><button disabled={busy} onClick={onClose} className="mt-3 w-full py-2 text-sm text-slate-400">Ahora no</button>
    </div>
  </div>;
}
