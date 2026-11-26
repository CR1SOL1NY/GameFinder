import { createContext, useContext } from 'react';
import type { Game } from '../games';
import type { Usuario } from '../authApi';
export type View = 'home' | 'results' | 'offers' | 'detail' | 'profile' | 'admin' | 'notfound';
export type Section = 'Mi perfil' | 'Lista de deseados' | 'Mis calificaciones' | 'Configuración' | 'Juegos comparados';
export interface Store { user: Usuario | null; wishlist: string[]; pendingWish: string[]; toggleWish: (game: Game) => Promise<void>; clearWish: () => Promise<void>; openGame: (id: string) => void; compareGame: (game: Game) => void; notify: (message: string) => void; requireLogin: (reason: string, then?: (user: Usuario) => void | Promise<void>) => void; refreshUser: () => Promise<void>; setUser: (user: Usuario) => void; logout: () => Promise<void> }
export const StoreContext = createContext<Store | null>(null);
export function useStore() { const store = useContext(StoreContext); if (!store) throw new Error('Store no disponible'); return store; }
export const CatalogContext = createContext<Game[]>([]);
export const useCatalog = () => useContext(CatalogContext);
