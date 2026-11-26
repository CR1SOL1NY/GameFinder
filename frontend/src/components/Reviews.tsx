import { useEffect, useState } from 'react';
import { useStore } from '../context/Store';
import { dateLabel } from '../games';
import { request, errorMessage } from '../services/http';
import { getReviews, saveReview, deleteReview, type Review } from '../services/reviews';
import { fieldCls, panel } from './common';
import { ErrorState } from './Status';
import { StarRatingInput, RatingStars } from './RatingStars';
export default function Reviews({gameId, changed}: {gameId: string; changed: ()=>void}) {
  const {user,requireLogin,notify}=useStore();
  const [reviews,setReviews]=useState<Review[]>([]),[mine,setMine]=useState<Review|null>(null),[stars,setStars]=useState(5),[text,setText]=useState(''),[writing,setWriting]=useState(false);
  const [error,setError]=useState(''),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[page,setPage]=useState(0),[reload,setReload]=useState(0);
  useEffect(()=>{
    const c=new AbortController();setLoading(true);setError('');
    Promise.all([getReviews(gameId,page*20,c.signal),user?request<Review|null>(`/calificaciones/mia/${gameId}`,{signal:c.signal}):Promise.resolve(null)]).then(([list,own])=>{setReviews(list);setMine(own);if(own){setStars(own.puntaje);setText(own.comentario);}}).catch(e=>{if(!c.signal.aborted)setError(errorMessage(e));}).finally(()=>{if(!c.signal.aborted)setLoading(false);});
    return ()=>c.abort();
  },[gameId,user?._id,page,reload]);
  async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{await saveReview(gameId,stars,text,mine?._id);notify('Calificación guardada');setWriting(false);setReload(n=>n+1);changed();}catch(e){setError(errorMessage(e));}finally{setBusy(false);}}
  async function remove(){if(!mine||!window.confirm('¿Eliminar tu calificación de este juego?'))return;setBusy(true);setError('');try{await deleteReview(mine._id);setMine(null);setText('');setWriting(false);notify('Calificación eliminada');setReload(n=>n+1);changed();}catch(e){setError(errorMessage(e));}finally{setBusy(false);}}
  return <section className="mt-6 space-y-4"><h2 className="text-xl font-bold">Calificaciones de la comunidad</h2>
    {loading?<p role="status" className="text-sm text-slate-400">Cargando calificaciones…</p>:<>
      <button onClick={()=>requireLogin('Inicia sesión para calificar este juego.',()=>setWriting(true))} className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-bold text-white">{mine?'Editar mi calificación':'Calificar este juego'}</button>
      {mine&&<button disabled={busy} onClick={()=>void remove()} className="ml-3 rounded-lg border border-rose-400/30 px-4 py-3 text-sm text-rose-300">Eliminar mi calificación</button>}
      {writing&&user&&<form onSubmit={submit} className={`${panel} space-y-4`}><StarRatingInput value={stars} onChange={setStars} disabled={busy}/><label className="block text-sm">Comentario (opcional)<textarea maxLength={2000} rows={4} value={text} onChange={e=>setText(e.target.value)} className={fieldCls}/></label><div className="flex gap-3"><button disabled={busy} className="rounded-lg bg-blue-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-40">{busy?'Guardando…':'Guardar calificación'}</button><button disabled={busy} type="button" onClick={()=>setWriting(false)} className="rounded-lg border border-blue-500/30 px-4 py-3 text-sm">Cancelar</button></div></form>}
      {!reviews.length&&!error&&<p className="text-sm text-slate-400">Todavía no hay calificaciones publicadas.</p>}
      {reviews.map(r=><article key={r._id} className={panel}><div className="flex flex-wrap justify-between gap-2 text-sm"><b>{r.nombreUsuario||'Usuario'} {r.usuarioId===user?._id&&'· Tú'}</b><RatingStars value={r.puntaje}/></div>{r.comentario&&<p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">{r.comentario}</p>}<p className="mt-2 text-xs text-slate-400">{dateLabel(r.fecha)}</p></article>)}
      {(page>0||reviews.length===20)&&<nav aria-label="Paginación de calificaciones" className="flex gap-3"><button disabled={!page} onClick={()=>setPage(p=>p-1)} className="rounded border border-blue-500/30 px-4 py-2 text-sm disabled:opacity-30">Anteriores</button><button disabled={reviews.length<20} onClick={()=>setPage(p=>p+1)} className="rounded border border-blue-500/30 px-4 py-2 text-sm disabled:opacity-30">Siguientes</button></nav>}
    </>}{error&&<ErrorState message={error} retry={()=>setReload(n=>n+1)}/>}</section>;
}
