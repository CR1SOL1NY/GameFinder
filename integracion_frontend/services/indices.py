"""Preparación idempotente: conservar índices completos con garantías compatibles."""
from collections.abc import Mapping
from pymongo.errors import OperationFailure


def campos_normalizados(campos):
    if isinstance(campos, str):
        return [(campos, 1)]
    if isinstance(campos, Mapping):
        return list(campos.items())
    return [tuple(campo) for campo in campos]


def collation_compatible(actual, esperada):
    actual, esperada = actual or {}, esperada or {}
    if actual.get('locale', 'simple') != esperada.get('locale', 'simple'):
        return False
    if esperada.get('locale', 'simple') == 'simple':
        return True
    # MongoDB devuelve estas opciones incluso cuando se omitieron al crear el
    # índice. La versión interna de ICU no es una opción solicitada por la app.
    predeterminados = {
        'strength': 3, 'caseLevel': False, 'caseFirst': 'off',
        'numericOrdering': False, 'alternate': 'non-ignorable',
        'maxVariable': 'punct', 'normalization': False, 'backwards': False,
    }
    return all(actual.get(k, v) == esperada.get(k, v) for k, v in predeterminados.items())


def indice_compatible(indice, campos, opciones):
    if campos_normalizados(indice.get('key', [])) != campos_normalizados(campos):
        return False
    if opciones.get('unique') and not indice.get('unique'):
        return False
    # Un índice único completo también cubre una consulta que solo necesita un
    # índice normal. Se conserva esa restricción más fuerte, sin reemplazarla.
    if bool(indice.get('sparse')) != bool(opciones.get('sparse')):
        return False
    if bool(indice.get('hidden')) != bool(opciones.get('hidden')):
        return False
    if indice.get('partialFilterExpression') != opciones.get('partialFilterExpression'):
        return False
    if indice.get('expireAfterSeconds') != opciones.get('expireAfterSeconds'):
        return False
    return collation_compatible(indice.get('collation'), opciones.get('collation'))


async def buscar_compatible(coleccion, campos, opciones):
    existentes = await coleccion.index_information()
    efectivas = dict(opciones)
    # Sin collation explícita, create_index hereda la de la colección. Solo
    # consultarla cuando hay un candidato no simple que necesita comparación.
    if 'collation' not in opciones and any(
        campos_normalizados(i.get('key', [])) == campos_normalizados(campos)
        and (i.get('collation') or {}).get('locale', 'simple') != 'simple'
        for i in existentes.values()
    ):
        configuracion = await coleccion.options()
        efectivas['collation'] = configuracion.get('collation')
    return next((nombre for nombre, indice in existentes.items()
                 if indice_compatible(indice, campos, efectivas)), None)


async def asegurar_indice(coleccion, campos, **opciones):
    existente = await buscar_compatible(coleccion, campos, opciones)
    if existente is not None:
        return existente
    try:
        return await coleccion.create_index(campos, **opciones)
    except OperationFailure as error:
        if error.code in (85, 86):
            # Otra réplica pudo crearlo entre la lectura y la creación. Releer
            # sus garantías; nunca ignorar un conflicto por nombre solamente.
            existente = await buscar_compatible(coleccion, campos, opciones)
            if existente is not None:
                return existente
        raise
