"""Faturas puxadas do software de faturação certificado (vivem na cloud).

NÃO geramos faturas aqui — uma fatura legal em PT só pode sair de software
certificado pela AT (ATCUD + QR + SAF-T). Este módulo PUXA as faturas por API e
associa-as ao cliente certo (cruzando NIF → email), para o portal as mostrar.

`Fatura` não herda `Sincronizavel`: vive só na cloud (a caixa local da oficina
não precisa de faturas), por isso fica fora do sync oficina↔cloud.
"""
from django.db import models


class Fatura(models.Model):
    class Estado(models.TextChoices):
        CASADA_NIF = 'casada_nif', 'Casada por NIF'
        CASADA_EMAIL = 'casada_email', 'Casada por email'
        MANUAL = 'manual', 'Atribuída manualmente'
        POR_RESOLVER = 'por_resolver', 'Por resolver'

    cliente = models.ForeignKey(
        'oficina.Cliente', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='faturas',
        help_text='A que cliente pertence. Pode ficar vazio até casar (estado "por resolver").')
    provedor = models.CharField('software', max_length=40)
    id_externo = models.CharField('ID no software', max_length=120)
    numero = models.CharField('número', max_length=60, blank=True)
    data = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    moeda = models.CharField(max_length=3, default='EUR')

    # Snapshot do que veio na fatura — serve para casar e para auditoria
    # (mantém o que o software tinha, mesmo que o cliente mude os dados depois).
    nif = models.CharField('NIF', max_length=20, blank=True)
    nome = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)

    pdf = models.FileField('PDF', upload_to='faturas/', blank=True)
    pdf_url = models.URLField('URL original', max_length=500, blank=True)

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.POR_RESOLVER)
    puxado_em = models.DateTimeField('puxado em', auto_now_add=True)

    class Meta:
        verbose_name = 'fatura'
        verbose_name_plural = 'faturas'
        ordering = ['-data', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['provedor', 'id_externo'], name='fatura_unica_por_provedor'),
        ]

    def __str__(self):
        return self.numero or f'{self.provedor}:{self.id_externo}'

    @property
    def tem_ficheiro(self):
        return bool(self.pdf) or bool(self.pdf_url)


class EstadoFaturacao(models.Model):
    """Marca de água por software: até quando já puxámos (para puxar só o novo)."""
    provedor = models.CharField(max_length=40, unique=True)
    ultimo = models.DateTimeField('último puxado', null=True, blank=True)

    class Meta:
        verbose_name = 'estado de faturação'
        verbose_name_plural = 'estados de faturação'

    def __str__(self):
        return f'{self.provedor}: {self.ultimo or "—"}'
