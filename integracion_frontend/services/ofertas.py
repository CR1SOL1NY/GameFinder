"""Ofertas independientes por tienda, plataforma y moneda, sin inferir asociaciones."""
import math
from datetime import datetime, timezone
from bson import ObjectId, Decimal128
from fastapi import HTTPException
from integracion_frontend.services.common import validar_id, minimo_clp, serializar


async def auditar(db, actual, accion, recurso):
    await db.registros.insert_one({'usuarioId': actual['_id'], 'accion': accion, 'recurso': recurso, 'fecha': datetime.now(timezone.utc)})


def validar_selector(plataforma, sin_plataforma):
    if plataforma is not None and sin_plataforma:
        raise HTTPException(422, 'Selecciona una plataforma o las ofertas sin plataforma, no ambas')


def coincide(p, plataforma=None, moneda=None, sin_plataforma=False):
    return ((plataforma is None or p.get('plataforma') == plataforma)
            and (moneda is None or p.get('moneda') == moneda)
            and (not sin_plataforma or not p.get('plataforma')))


def clave(p):
    return str(p.get('tiendaId')), p.get('plataforma') or None, p.get('moneda')


def precio_numerico(p):
    value = p.get('precio')
    if isinstance(value, Decimal128):
        value = float(value.to_decimal())
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


async def consultar_ofertas(db, juego_id, plataforma=None, moneda=None, sin_plataforma=False):
    validar_selector(plataforma, sin_plataforma)
    game = await db.juegos.find_one({'_id': validar_id(juego_id), 'activo': {'$ne': False}})
    if not game:
        raise HTTPException(404, 'Juego no encontrado')
    prices = game.get('precios', [])
    selected = [p for p in prices if coincide(p, plataforma, moneda, sin_plataforma)]
    ids = [validar_id(str(p['tiendaId'])) for p in selected if ObjectId.is_valid(str(p.get('tiendaId', '')))]
    stores = {str(t['_id']): t async for t in db.tiendas.find({'_id': {'$in': ids}})}
    offers = [{**p, 'nombre': stores.get(str(p.get('tiendaId')), {}).get('nombre'), 'url_base': stores.get(str(p.get('tiendaId')), {}).get('url_base')} for p in selected]
    offers.sort(key=lambda p: (str(p.get('plataforma') or ''), str(p.get('moneda') or ''), precio_numerico(p) if precio_numerico(p) is not None else float('inf')))
    groups = {}
    for p in offers:
        amount = precio_numerico(p)
        # No comparar registros de moneda desconocida ni atribuir un mínimo a una plataforma desconocida.
        if not p.get('plataforma') or not isinstance(p.get('moneda'), str) or len(p['moneda']) != 3 or not p['moneda'].isascii() or not p['moneda'].isalpha() or not p['moneda'].isupper() or amount is None:
            continue
        key = p['plataforma'], p['moneda']
        group = groups.setdefault(key, {'plataforma': key[0], 'moneda': key[1], 'totalOfertas': 0, 'precioMinimo': amount, 'tiendaId': p.get('tiendaId')})
        group['totalOfertas'] += 1
    return serializar({
        'juegoId': juego_id, 'titulo': game['titulo'], 'totalOfertas': len(offers), 'ofertas': offers,
        'plataformas': sorted(set(game.get('plataformas', [])) | {p['plataforma'] for p in prices if p.get('plataforma')}),
        'monedas': sorted({p['moneda'] for p in prices if p.get('moneda')}),
        'ofertasSinPlataforma': sum(not p.get('plataforma') for p in offers),
        'resumen': list(groups.values()),
    })


async def cambiar_oferta(db, juego_id, tienda_id, actual, accion, datos=None, plataforma=None, moneda=None, sin_plataforma=False, oferta_id=None):
    validar_selector(plataforma, sin_plataforma)
    gid = validar_id(juego_id)
    tid = validar_id(tienda_id) if tienda_id is not None else None
    if oferta_id is not None:
        validar_id(oferta_id)
    if accion == 'agregar' and not await db.tiendas.find_one({'_id': tid}):
        raise HTTPException(404, 'Tienda no encontrada')
    for _ in range(3):
        game = await db.juegos.find_one({'_id': gid})
        if not game:
            raise HTTPException(404, 'Juego no encontrado')
        if datos and datos.get('plataforma') and datos['plataforma'] not in game.get('plataformas', []):
            raise HTTPException(422, 'La plataforma de la oferta debe estar registrada en el videojuego')
        prices = game.get('precios', [])
        if accion == 'agregar':
            new = {**datos, 'ofertaId': str(ObjectId()), 'tiendaId': tid, 'fechaActualizacion': datetime.now(timezone.utc)}
            await validar_plataforma_tienda(db, game, new)
            if any(clave(p) == clave(new) for p in prices):
                raise HTTPException(409, 'Ya existe una oferta de esta tienda, plataforma y moneda')
            result = [*prices, new]
        else:
            matches = [i for i, p in enumerate(prices) if
                       (str(p.get('ofertaId')) == oferta_id if oferta_id is not None else
                        str(p.get('tiendaId')) == str(tid) and coincide(p, plataforma, moneda, sin_plataforma))]
            if not matches:
                raise HTTPException(404, 'Oferta no encontrada')
            if len(matches) > 1:
                raise HTTPException(409, 'Hay varias ofertas; especifica plataforma y moneda o utiliza el identificador de oferta')
            index = matches[0]
            result = [{**p} for p in prices]
            if accion == 'quitar':
                result.pop(index)
            else:
                new = {**prices[index], **datos, 'ofertaId': prices[index].get('ofertaId') or str(ObjectId())}
                await validar_plataforma_tienda(db, game, new)
                if any(i != index and clave(p) == clave(new) for i, p in enumerate(prices)):
                    raise HTTPException(409, 'Ya existe una oferta de esta tienda, plataforma y moneda')
                # Clasificar una oferta no implica que se haya vuelto a verificar su precio.
                if any(k in datos and datos[k] != prices[index].get(k) for k in ('precio', 'moneda')):
                    new['fechaActualizacion'] = datetime.now(timezone.utc)
                result[index] = new
        updated = await db.juegos.update_one({'_id': gid, 'precios': game.get('precios')}, {'$set': {'precios': result, 'precio_mas_barato': minimo_clp(result)}})
        if updated.matched_count:
            await auditar(db, actual, accion + '_oferta', juego_id)
            return serializar({'mensaje': 'Ofertas actualizadas', 'precios': result, 'precio_mas_barato': minimo_clp(result)})
    raise HTTPException(409, 'Las ofertas cambiaron simultáneamente; vuelve a intentar')


async def validar_plataforma_tienda(db, juego, oferta):
    """La relación se verifica en servidor también para escrituras heredadas."""
    tienda = await db.tiendas.find_one({'_id': validar_id(str(oferta.get('tiendaId')))})
    if not tienda:
        raise HTTPException(404, 'Tienda no encontrada')
    plataforma = oferta.get('plataforma')
    if plataforma and plataforma not in (juego.get('plataformas') or []):
        raise HTTPException(422, 'La plataforma de la oferta debe estar registrada en el videojuego')
    admitidas = tienda.get('plataformas')
    # Los documentos antiguos sin configuración permanecen legibles; no se infiere soporte.
    if isinstance(admitidas, list) and admitidas:
        if not plataforma:
            raise HTTPException(422, 'Esta tienda tiene plataformas configuradas: indica la plataforma de la oferta')
        if plataforma not in admitidas:
            raise HTTPException(422, 'La tienda no vende para la plataforma de esta oferta')
