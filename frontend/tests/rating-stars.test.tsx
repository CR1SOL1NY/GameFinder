import { useState } from 'react';
import { it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StarRatingInput, RatingStars } from '../src/components/RatingStars';

it('selecciona medias estrellas sin un menú desplegable', async () => {
  function Controlled() { const [value, setValue] = useState(5); return <StarRatingInput value={value} onChange={setValue} />; }
  const u = userEvent.setup();
  render(<Controlled />);
  expect(screen.queryByRole('combobox')).toBeNull();
  expect(screen.getAllByRole('radio')).toHaveLength(10);
  await u.click(screen.getByRole('radio', { name: '3,5 de 5 estrellas' }));
  expect((screen.getByRole('radio', { name: '3,5 de 5 estrellas' }) as HTMLInputElement).checked).toBe(true);
  expect(screen.getByText('3,5 / 5')).toBeTruthy();
  await u.click(screen.getByRole('radio', { name: '0,5 de 5 estrellas' }));
  expect(screen.getByText('0,5 / 5')).toBeTruthy();
});

it('permite seleccionar con teclado en pasos de media estrella', async () => {
  function Controlled() { const [value, setValue] = useState(3.5); return <StarRatingInput value={value} onChange={setValue} />; }
  const u = userEvent.setup();
  render(<Controlled />);
  await u.tab();
  expect(document.activeElement).toBe(screen.getByRole('radio', { name: '3,5 de 5 estrellas' }));
  await u.keyboard('[ArrowRight]');
  expect(screen.getByText('4 / 5')).toBeTruthy();
  await u.keyboard('[ArrowLeft]');
  expect(screen.getByText('3,5 / 5')).toBeTruthy();
});

it('representa una puntuación fraccionaria también al leer una reseña', () => {
  render(<RatingStars value={3.5} />);
  const stars = screen.getByRole('img', { name: '3,5 de 5 estrellas' });
  expect(stars.querySelector('[style*="50%"]')).toBeTruthy();
});

it('bloquea la edición mientras se guarda la reseña', async () => {
  const change = vi.fn();
  render(<StarRatingInput value={4.5} onChange={change} disabled />);
  await userEvent.setup().click(screen.getByRole('radio', { name: '2,5 de 5 estrellas' }));
  expect(change).not.toHaveBeenCalled();
});
