import { request, jsonBody } from './http';
export interface Review { _id: string; usuarioId: string; juegoId: string; puntaje: number; comentario: string; fecha: string; nombreUsuario?: string; juego?: { _id: string; titulo: string; imagenPortada?: string } | null }
export const getReviews = (id: string, skip = 0, signal?: AbortSignal) => request<Review[]>(`/calificaciones/juego/${id}?skip=${skip}&limit=20`, {signal});
export const myReviews = (skip = 0, signal?: AbortSignal) => request<Review[]>(`/usuarios/me/calificaciones?skip=${skip}`, {signal});
export const saveReview = (gameId: string, puntaje: number, comentario: string, reviewId?: string) => request<Review>(reviewId ? `/calificaciones/${reviewId}` : '/calificaciones/', jsonBody(reviewId ? 'PUT' : 'POST', reviewId ? {puntaje, comentario} : {juegoId: gameId, puntaje, comentario}));
export const deleteReview = (id: string) => request(`/calificaciones/${id}`, {method: 'DELETE'});

export interface ReviewSummary { total: number; promedio: number | null; ultimas: Review[] }
export const reviewSummary = (signal?: AbortSignal) => request<ReviewSummary>('/usuarios/me/resumen-calificaciones', { signal });
