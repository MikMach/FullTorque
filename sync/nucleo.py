"""Núcleo da sincronização: serializar, recolher alterações e aplicar (LWW)."""
import uuid as uuidlib
from datetime import date, datetime
from decimal import Decimal

from django.utils.dateparse import parse_datetime

from .registo import REGISTO

_CFG = {Mod.__name__: (Mod, campos, fks) for Mod, _d, campos, fks in REGISTO}
_ORDEM = {Mod.__name__: i for i, (Mod, *_r) in enumerate(REGISTO)}


def _json(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, uuidlib.UUID):
        return str(valor)
    return valor


def serializar(obj, campos, fks):
    dados = {c: _json(getattr(obj, c)) for c in campos}
    refs = {}
    for campo in fks:
        rel = getattr(obj, campo)
        refs[campo] = str(rel.uuid) if rel is not None else None
    return {
        'modelo': type(obj).__name__,
        'uuid': str(obj.uuid),
        'atualizado_em': obj.atualizado_em.isoformat(),
        'dados': dados,
        'fks': refs,
    }


def recolher(direcoes, desde):
    """Records dos modelos nas `direcoes` dadas, alterados depois de `desde`."""
    lote, maximo = [], desde
    for Modelo, direcao, campos, fks in REGISTO:
        if direcao not in direcoes:
            continue
        qs = Modelo.objects.all()
        if desde:
            qs = qs.filter(atualizado_em__gt=desde)
        for obj in qs.order_by('atualizado_em'):
            lote.append(serializar(obj, campos, fks))
            if maximo is None or obj.atualizado_em > maximo:
                maximo = obj.atualizado_em
    return lote, maximo


def aplicar_lote(lote):
    aplicados = ignorados = 0
    for rec in sorted(lote, key=lambda r: _ORDEM.get(r['modelo'], 999)):
        if _aplicar_um(rec):
            aplicados += 1
        else:
            ignorados += 1
    return aplicados, ignorados


def _aplicar_um(rec):
    item = _CFG.get(rec['modelo'])
    if not item:
        return False
    Modelo, campos, fks = item
    atualizado = parse_datetime(rec['atualizado_em'])

    data = {}
    for c in campos:
        raw = rec['dados'].get(c)
        data[c] = Modelo._meta.get_field(c).to_python(raw) if raw is not None else None
    for campo, FkModelo in fks.items():
        ref = rec['fks'].get(campo)
        if ref:
            rel = FkModelo.objects.filter(uuid=ref).only('pk', 'atualizado_em').first()
            if rel is None:
                return False  # dependência ainda não sincronizada; ignora (entra na próxima ronda)
            data[campo + '_id'] = rel.pk
        else:
            data[campo + '_id'] = None
    data['atualizado_em'] = atualizado

    existente = Modelo.objects.filter(uuid=rec['uuid']).first()
    if existente:
        if atualizado and existente.atualizado_em and atualizado <= existente.atualizado_em:
            return False  # last-write-wins: o local é mais recente ou igual
        Modelo.objects.filter(pk=existente.pk).update(**data)
    else:
        Modelo(uuid=rec['uuid'], **data).save(sincronizando=True)
    return True
