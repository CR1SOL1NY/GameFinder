import type React from 'react';
export type IconName = 'search' | 'heart' | 'bell' | 'user' | 'grid' | 'tag' | 'home' | 'gamepad' | 'arrow' | 'shield' | 'monitor' | 'star' | 'filter' | 'check' | 'settings' | 'sun' | 'moon' | 'trash' | 'back' | 'lock';
export function Icon({ name, className = 'size-5', filled = false }: { name: IconName; className?: string; filled?: boolean }) {
  const paths: Record<IconName, React.ReactNode> = {
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
    heart: <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5a5.5 5.5 0 0 0 1-8.9Z" />,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></>,
    user: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    tag: <><path d="M20.6 13.6 11 23l-9-9 9.6-9.6H20v8.4Z" /><circle cx="16" cy="8" r="1" /></>,
    home: <><path d="m3 11 9-8 9 8" /><path d="M5 10v11h14V10M9 21v-7h6v7" /></>,
    gamepad: <><path d="M8 12h4m-2-2v4M16 11h.01M18 13h.01" /><path d="M8.5 6h7A6.5 6.5 0 0 1 22 12.5V16a3 3 0 0 1-5.1 2.1L15 16H9l-1.9 2.1A3 3 0 0 1 2 16v-3.5A6.5 6.5 0 0 1 8.5 6Z" /></>,
    arrow: <><path d="M5 12h14" /><path d="m15 8 4 4-4 4" /></>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" /><path d="m9 12 2 2 4-4" /></>,
    monitor: <><rect x="2" y="3" width="20" height="14" rx="2" /><path d="M8 21h8M12 17v4" /></>,
    star: <path d="m12 2.5 3 6 6.5 1-4.7 4.6 1.1 6.4-5.9-3.1-5.9 3.1 1.1-6.4-4.7-4.6 6.5-1 3-6Z" />,
    filter: <path d="M4 6h16M7 12h10M10 18h4" />,
    check: <path d="m5 12 4 4L19 6" />,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />,
    trash: <><path d="M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15" /></>,
    lock: <><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></>,
    back: <><path d="M19 12H5" /><path d="m9 8-4 4 4 4" /></>,
  };
  return <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" className={className} fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

export type PlatformKey = 'PC' | 'PlayStation' | 'Xbox' | 'Switch';
export const platformBrand: Record<PlatformKey, { label: string; bg: string; ring: string }> = {
  PC: { label: 'PC', bg: '#111111', ring: '#8b8b8b' },
  PlayStation: { label: 'PlayStation', bg: '#0070d1', ring: '#5db3ff' },
  Xbox: { label: 'Xbox', bg: '#107c10', ring: '#5fd45f' },
  Switch: { label: 'Nintendo Switch', bg: '#e60012', ring: '#ff7a84' },
};
export function PlatformLogo({ name, className = 'size-6' }: { name: PlatformKey; className?: string }) {
  const c = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' } as const;
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      {name === 'PC' && <g {...c}><rect x="2.5" y="4" width="19" height="13" rx="2" /><path d="M8 21h8M12 17v4" /></g>}
      {name === 'PlayStation' && <g {...c}><path d="M6 3.5 9 8.5H3Z" /><circle cx="18" cy="6" r="3" /><path d="m3.5 14.5 5 5m0-5-5 5" /><rect x="15" y="14.5" width="5.5" height="5.5" rx=".5" /></g>}
      {name === 'Xbox' && <g {...c}><circle cx="12" cy="12" r="9.5" /><path d="m7.5 7.5 9 9m0-9-9 9" /></g>}
      {name === 'Switch' && <g {...c}><rect x="3" y="3.5" width="7" height="17" rx="3" /><rect x="14" y="3.5" width="7" height="17" rx="3" /><circle cx="6.5" cy="9" r="1.2" fill="currentColor" /><circle cx="17.5" cy="15" r="1.2" fill="currentColor" /></g>}
    </svg>
  );
}

export const Img = ({ src, fallback, className, alt = '' }: { src: string; fallback: string; className?: string; alt?: string }) => (
  <img src={src} alt={alt} loading="lazy" className={className} onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = fallback; }} />
);


export const panel = 'rounded-xl border border-blue-500/20 bg-panel p-4';
export const fieldCls = 'mt-1.5 w-full rounded-lg border border-blue-500/25 bg-field px-3 py-2.5 text-sm outline-none focus:border-blue-400';
