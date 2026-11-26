import { afterEach, vi } from 'vitest';
import { cleanup, configure } from '@testing-library/react';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
// Bcrypt y HTTP pueden superar el segundo bajo carga de CI; esperamos una condición real.
configure({asyncUtilTimeout:5000});
window.scrollTo=()=>{};
