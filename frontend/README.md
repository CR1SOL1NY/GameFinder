# Frontend de GameFinder

React, TypeScript, Vite y Tailwind CSS v4. Esta carpeta incorpora el frontend existente del equipo, conservando su diseño y sus componentes.

La integración se realiza en la rama `funcionalidad/integracion-frontend`, mediante cambios separados de configuración, componentes, páginas, conexión con FastAPI y pruebas.

Requisito: Node.js 24. Para instalar las dependencias, en la **terminal del FRONTEND**, dentro de esta carpeta:

```powershell
npm.cmd ci
npm.cmd run dev
```

La web se abre en `http://localhost:5173`. En otra terminal debe estar ejecutándose `main_interfaz:app` desde la raíz del repositorio. Vite utiliza `/api` y reenvía al contrato `/interfaz` de FastAPI. El backend original permanece en la raíz; no hay que buscar una carpeta `backend` nueva.

La URL del servicio se configura con `.env.example`. No se deben incluir credenciales de MongoDB en variables `VITE_*` ni en el código del navegador. Esta integración no despliega la aplicación ni ejecuta operaciones sobre Atlas.

En la **terminal del FRONTEND**:

```powershell
npm.cmd test
npm.cmd run build
```

Consulta [la guía de integración](../docs/INTEGRACION_FRONTEND.md) para instalación del backend, pruebas completas, origen del código y límites. Configura el directorio raíz de Vercel como `frontend` para que use la regla de `vercel.json` y reenvíe `/api` al backend de Render.
