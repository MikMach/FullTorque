from django.db import models


class SyncEstado(models.Model):
    """Marca de água da sincronização (guardada no servidor local/cliente)."""

    chave = models.CharField(max_length=20, unique=True)  # 'push' | 'pull'
    ultimo = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'estado de sincronização'
        verbose_name_plural = 'estados de sincronização'

    def __str__(self):
        return f'{self.chave}: {self.ultimo:%Y-%m-%d %H:%M:%S}' if self.ultimo else f'{self.chave}: nunca'

    @classmethod
    def marca(cls, chave):
        obj, _ = cls.objects.get_or_create(chave=chave)
        return obj
