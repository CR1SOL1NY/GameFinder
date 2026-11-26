import { request, jsonBody } from './services/http';
import { obtenerTiendas, mapearJuego, type JuegoAPI } from './api';
export interface Preferencias { precioMin: number; precioMax: number; generos: string[]; plataformas: string[] }
export interface Usuario { _id: string; nombre: string; correo: string; rol?: string; fechaRegistro: string; preferencias?: Preferencias | null; listaDeseados?: { juegoId: string; fechaAgregado: string }[] }
export const miPerfil = (signal?: AbortSignal) => request<Usuario>('/usuarios/me', {signal});
export async function iniciarSesion(correo: string, contrasena: string) { await request('/usuarios/login', jsonBody('POST', {correo, contrasena})); return miPerfil(); }
export async function registrarUsuario(nombre: string, correo: string, contrasena: string) { await request('/usuarios/', jsonBody('POST', {nombre, correo, contrasena})); return iniciarSesion(correo, contrasena); }
export const cerrarSesion = () => request('/usuarios/logout', {method: 'POST'});
export const guardarPerfil = (userId: string, nombre: string, preferencias: Preferencias) => request<Usuario>(`/usuarios/${userId}`, jsonBody('PUT', {nombre, preferencias}));
export const guardarDeseado = (userId: string, juegoId: string) => request(`/usuarios/${userId}/deseados/${juegoId}`, {method: 'PUT'});
export const quitarDeseado = (userId: string, juegoId: string) => request(`/usuarios/${userId}/deseados/${juegoId}`, {method: 'DELETE'});
export const listaDeseados = async (userId: string) => (await request<{listaDeseados: {juegoId: string}[]}>(`/usuarios/${userId}/deseados`)).listaDeseados.map(x => x.juegoId);
export async function recomendaciones(userId: string, signal?: AbortSignal) { const [result, tiendas] = await Promise.all([request<{ recomendaciones: JuegoAPI[] }>(`/usuarios/${userId}/recomendaciones`, {signal}), obtenerTiendas()]); return result.recomendaciones.map(g => mapearJuego(g, tiendas)); }
