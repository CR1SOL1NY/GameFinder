import { Component, type ReactNode } from 'react';
export default class ErrorBoundary extends Component<{children:ReactNode},{failed:boolean}> {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  render(){if(this.state.failed)return <main className="grid min-h-screen place-items-center bg-app px-5 text-center text-fg"><div className="max-w-lg rounded-xl border border-blue-500/30 bg-panel p-8"><h1 className="text-2xl font-black">No pudimos mostrar esta página</h1><p className="mt-3 text-sm text-slate-300">Vuelve al inicio para intentar nuevamente.</p><button onClick={()=>window.location.assign('/')} className="mt-5 rounded-lg bg-blue-600 px-5 py-3 text-sm font-bold text-white">Volver al inicio</button></div></main>;return this.props.children;}
}
