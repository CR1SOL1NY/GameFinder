# Frontend de GameFinder

React, TypeScript, Vite y Tailwind CSS v4. Esta carpeta incorpora el frontend existente del equipo, conservando su diseño y sus componentes.

La integración se realiza en la rama `funcionalidad/integracion-frontend`, mediante cambios separados de configuración, componentes, páginas, conexión con FastAPI y pruebas. Esta primera etapa prepara las herramientas; las pantallas se incorporan en las siguientes subidas.

Requisito: Node.js 24. Para instalar las dependencias, en la **terminal del FRONTEND**, dentro de esta carpeta:

```powershell
npm.cmd ci
```

La URL del servicio se configura con `.env.example`. No se deben incluir credenciales de MongoDB en variables `VITE_*` ni en el código del navegador. Esta integración no despliega la aplicación ni ejecuta operaciones sobre Atlas.
