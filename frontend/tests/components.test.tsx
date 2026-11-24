import { describe,it,expect,vi } from 'vitest';
import { fireEvent,render,screen,within,waitFor } from '@testing-library/react';
import LoginModal from '../src/components/LoginModal';
import { readRoute } from '../src/context/router';
describe('Rutas y formularios',()=>{
  it('reconoce fichas, filtros y páginas desconocidas',()=>{history.replaceState(null,'','/juegos/123');expect(readRoute().gameId).toBe('123');history.replaceState(null,'','/catalogo?q=Prueba&genero=RPG');expect(readRoute().search.get('genero')).toBe('RPG');history.replaceState(null,'','/no-existe');expect(readRoute().view).toBe('notfound');});
  it('presenta el error del servidor y conserva el formulario',async()=>{vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({detail:'Correo o contraseña incorrectos'}),{status:401})));const success=vi.fn();render(<LoginModal reason="Prueba" onConfirm={success} onClose={()=>{}}/>);fireEvent.change(screen.getByLabelText('Correo electrónico'),{target:{value:'prueba@example.com'}});fireEvent.change(screen.getByLabelText('Contraseña'),{target:{value:'Incorrecta123'}});fireEvent.submit(screen.getByRole('button',{name:'Iniciar sesión'}).closest('form')!);await waitFor(()=>expect(screen.getByRole('alert').textContent).toContain('incorrectos'));expect(success).not.toHaveBeenCalled();vi.unstubAllGlobals();});
});
