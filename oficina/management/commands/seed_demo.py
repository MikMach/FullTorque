"""Popula a base de dados com dados de demonstração realistas.

Uso:
    python manage.py seed_demo            # cria se a BD estiver vazia
    python manage.py seed_demo --reset    # apaga dados operacionais e recria

Cria: grupos de permissões, catálogo (marcas/modelos/serviços/peças), locais,
funcionários com login, clientes, viaturas, histórico de serviços (append-only),
inspeções, orçamentos e marcações.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from oficina.models import (
    Cliente, Funcionario, Inspecao, ItemInspecao, ItemOrcamento, Local, Marca,
    Marcacao, Modelo, Orcamento, Peca, PecaServico, RegistoServico, StockPeca,
    TipoServico, Viatura, OrdemTrabalho, SessaoTrabalho, ItemOrdem, FotoOrdem,
)

User = get_user_model()

# Catálogo de marcas/modelos vive em oficina/catalogo.py (comando seed_catalogo).

TIPOS_SERVICO = [
    # (nome, preço base, intervalo_km, intervalo_meses, descrição)
    ('Revisão completa', 120, 15000, 12, 'Revisão segundo o plano do fabricante.'),
    ('Mudança de óleo', 60, 15000, 12, 'Óleo + filtro de óleo.'),
    ('Travões — discos e pastilhas', 180, None, None, 'Substituição de discos e pastilhas.'),
    ('Diagnóstico eletrónico', 45, None, None, 'Leitura de erros e avaliação.'),
    ('Pneus & alinhamento', 80, None, None, 'Substituição de pneus e alinhamento de direção.'),
    ('Ar condicionado — recarga', 70, None, 24, 'Recarga de gás e higienização.'),
    ('Distribuição (correia)', 400, 120000, None, 'Substituição da correia/kit de distribuição.'),
    ('Inspeção pré-IPO', 30, None, None, 'Verificação prévia à Inspeção Periódica Obrigatória.'),
]

PECAS = [
    ('OL-5W30', 'Óleo 5W30 (1L)', '12.50'),
    ('FLT-OIL', 'Filtro de óleo', '9.90'),
    ('FLT-AIR', 'Filtro de ar', '14.00'),
    ('FLT-CAB', 'Filtro de habitáculo', '16.50'),
    ('BRK-PAD', 'Pastilhas de travão (jogo)', '45.00'),
    ('BRK-DISC', 'Disco de travão', '60.00'),
    ('BAT-60', 'Bateria 60Ah', '95.00'),
    ('SPK-PLUG', 'Vela de ignição', '8.00'),
    ('WIP-BLADE', 'Escovas limpa-vidros (par)', '18.00'),
    ('TIRE-205', 'Pneu 205/55 R16', '85.00'),
]

CLIENTES = [
    'António Ferreira', 'Sofia Marques', 'Carlos Oliveira', 'Inês Rodrigues',
    'Miguel Sousa', 'Ana Pereira', 'Tiago Almeida', 'Rita Carvalho',
    'Bruno Lopes', 'Helena Martins',
]

PONTOS_INSPECAO = [
    'Travões dianteiros', 'Travões traseiros', 'Pneus', 'Nível de óleo',
    'Filtro de ar', 'Bateria', 'Luzes', 'Suspensão', 'Líquido de refrigeração',
    'Limpa para-brisas',
]

COMBUSTIVEIS = [c[0] for c in Viatura.Combustivel.choices]
CORES = ['Branco', 'Preto', 'Cinzento', 'Azul', 'Vermelho', 'Prata']


class Command(BaseCommand):
    help = 'Popula a base de dados com dados de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Apaga dados operacionais antes de recriar.')

    def handle(self, *args, **options):
        random.seed(42)
        self.hoje = timezone.localdate()

        if options['reset']:
            self._reset()
        elif Viatura.objects.exists():
            self.stdout.write(self.style.WARNING(
                'Já existem dados. Usa --reset para apagar e recriar. Nada feito.'))
            return

        self._grupos()
        self._dono()
        call_command('seed_catalogo')
        modelos = list(Modelo.objects.filter(ativo=True))
        tipos = self._tipos_servico()
        pecas = self._pecas()
        locais = self._locais()
        self._stock(pecas, locais)
        funcionarios = self._funcionarios(locais)
        clientes = self._clientes()
        viaturas = self._viaturas(clientes, modelos, locais)
        self._cliente_login(clientes[0])
        self._historico(viaturas, tipos, funcionarios, pecas)
        self._inspecoes(viaturas, funcionarios)
        self._orcamentos(viaturas, tipos, funcionarios, pecas)
        self._marcacoes(viaturas, tipos, funcionarios)
        self._ordens(viaturas, tipos, funcionarios, pecas)

        self.stdout.write(self.style.SUCCESS('\n✓ Demo data criada com sucesso.'))
        self.stdout.write('  Funcionários (admin): joao@fulltorque.pt / maria@fulltorque.pt / pedro@fulltorque.pt — password: demo12345')
        self.stdout.write('  Cliente (portal): cliente@fulltorque.pt — password: demo12345')
        self.stdout.write('  Tablet (PIN): João 1234 · Maria 2345 · Pedro 3456')

    # ------------------------------------------------------------------ reset
    def _reset(self):
        self.stdout.write('A apagar dados operacionais...')
        # Ordem: filhos antes de pais (FKs PROTECT). queryset.delete() ignora o
        # guard append-only do RegistoServico — aceitável num comando de seed.
        FotoOrdem.objects.all().delete()
        OrdemTrabalho.objects.all().delete()   # cascata: sessões + itens
        PecaServico.objects.all().delete()
        for m in (Orcamento, Inspecao, Marcacao):
            m.objects.all().delete()
        RegistoServico.objects.all().delete()
        Viatura.objects.all().delete()
        StockPeca.objects.all().delete()
        Peca.objects.all().delete()
        Funcionario.objects.all().delete()
        Cliente.objects.all().delete()
        Modelo.objects.all().delete()
        Marca.objects.all().delete()
        TipoServico.objects.all().delete()
        Local.objects.all().delete()
        User.objects.filter(papel__in=[User.Papel.FUNCIONARIO, User.Papel.CLIENTE]).delete()

    # ----------------------------------------------------------------- grupos
    def _grupos(self):
        grupo, _ = Group.objects.get_or_create(name='Funcionário')
        oficina_perms = Permission.objects.filter(content_type__app_label='oficina')
        # Ver tudo (listas + autocomplete dos formulários)
        perms = list(oficina_perms.filter(codename__startswith='view_'))
        # Criar/editar nos modelos operacionais
        operacionais = ['viatura', 'cliente', 'inspecao', 'iteminspecao', 'orcamento',
                        'itemorcamento', 'marcacao', 'pecaservico', 'fotoregisto',
                        'ordemtrabalho', 'sessaotrabalho', 'itemordem', 'fotoordem']
        for model in operacionais:
            for acao in ('add', 'change'):
                p = oficina_perms.filter(codename=f'{acao}_{model}').first()
                if p:
                    perms.append(p)
        # Registos: append-only -> só criar
        p = oficina_perms.filter(codename='add_registoservico').first()
        if p:
            perms.append(p)
        grupo.permissions.set(perms)
        self.stdout.write(f'  Grupo "Funcionário" com {len(perms)} permissões.')

    # -------------------------------------------------------------- catálogos
    def _dono(self):
        user, criado = User.objects.get_or_create(email='dono@fulltorque.pt', defaults={
            'first_name': 'Rui', 'papel': User.Papel.DONO,
            'is_staff': True, 'is_superuser': True})
        if criado:
            user.set_password('FullTorque2026')
            user.save()
        self.stdout.write('  Dono (superuser): dono@fulltorque.pt' + (' [novo]' if criado else ''))

    def _tipos_servico(self):
        tipos = {}
        for nome, preco, km, meses, desc in TIPOS_SERVICO:
            t, _ = TipoServico.objects.get_or_create(nome=nome, defaults={
                'preco_base': Decimal(preco), 'intervalo_km': km,
                'intervalo_meses': meses, 'descricao': desc})
            tipos[nome] = t
        self.stdout.write(f'  {len(tipos)} tipos de serviço.')
        return tipos

    def _pecas(self):
        pecas = {}
        for ref, nome, preco in PECAS:
            p, _ = Peca.objects.get_or_create(referencia=ref, defaults={
                'nome': nome, 'preco_venda': Decimal(preco)})
            pecas[ref] = p
        self.stdout.write(f'  {len(pecas)} peças.')
        return pecas

    def _locais(self):
        dados = [
            ('Full Torque — Lisboa', 'Av. da República, 100', '1050-198', 'Lisboa', '210 000 000'),
            ('Full Torque — Porto', 'Rua de Santa Catarina, 200', '4000-447', 'Porto', '220 000 000'),
        ]
        locais = []
        for nome, morada, cp, cidade, tel in dados:
            local, _ = Local.objects.get_or_create(nome=nome, defaults={
                'slug': self._slug(nome), 'morada': morada, 'codigo_postal': cp,
                'cidade': cidade, 'telefone': tel, 'email': 'geral@fulltorque.pt'})
            locais.append(local)
        self.stdout.write(f'  {len(locais)} locais.')
        return locais

    def _stock(self, pecas, locais):
        n = 0
        for peca in pecas.values():
            for local in locais:
                StockPeca.objects.get_or_create(peca=peca, local=local, defaults={
                    'quantidade': random.randint(0, 30), 'stock_minimo': 4})
                n += 1
        self.stdout.write(f'  {n} registos de stock.')

    def _funcionarios(self, locais):
        dados = [
            ('joao@fulltorque.pt', 'João', 'Silva', 'Mecânico', locais[0], '1234'),
            ('maria@fulltorque.pt', 'Maria', 'Santos', 'Rececionista', locais[0], '2345'),
            ('pedro@fulltorque.pt', 'Pedro', 'Costa', 'Mecânico', locais[1], '3456'),
        ]
        grupo = Group.objects.get(name='Funcionário')
        funcionarios = []
        for email, nome, apelido, cargo, local, pin in dados:
            user, created = User.objects.get_or_create(email=email, defaults={
                'first_name': nome, 'last_name': apelido,
                'papel': User.Papel.FUNCIONARIO, 'is_staff': True})
            if created:
                user.set_password('demo12345')
                user.save()
            user.groups.add(grupo)
            func, _ = Funcionario.objects.get_or_create(user=user, defaults={
                'nome': f'{nome} {apelido}', 'cargo': cargo, 'local': local,
                'data_admissao': self.hoje - timedelta(days=random.randint(200, 1500))})
            func.set_pin(pin)
            func.save(update_fields=['pin'])
            funcionarios.append(func)
        self.stdout.write(f'  {len(funcionarios)} funcionários (login + PIN).')
        return funcionarios

    def _clientes(self):
        clientes = []
        for i, nome in enumerate(CLIENTES):
            primeiro = nome.split()[0].lower()
            c, _ = Cliente.objects.get_or_create(nome=nome, defaults={
                'telefone': f'9{random.randint(10000000, 99999999)}',
                'email': f'{primeiro}{i}@exemplo.pt',
                'nif': str(random.randint(200000000, 299999999))})
            clientes.append(c)
        self.stdout.write(f'  {len(clientes)} clientes.')
        return clientes

    def _cliente_login(self, cliente):
        user, created = User.objects.get_or_create(email='cliente@fulltorque.pt', defaults={
            'first_name': cliente.nome.split()[0], 'last_name': ' '.join(cliente.nome.split()[1:]),
            'papel': User.Papel.CLIENTE})
        if created:
            user.set_password('demo12345')
            user.save()
        cliente.user = user
        cliente.save(update_fields=['user'])
        self.stdout.write(f'  Login de cliente demo: cliente@fulltorque.pt (→ {cliente.nome}).')

    def _viaturas(self, clientes, modelos, locais):
        viaturas = []
        usadas = set()
        # IPO variada: alguns expirados, alguns a vencer (30d), maioria válida
        ipo_opcoes = (
            [self.hoje - timedelta(days=random.randint(5, 90)) for _ in range(3)] +
            [self.hoje + timedelta(days=random.randint(3, 28)) for _ in range(3)] +
            [self.hoje + timedelta(days=random.randint(90, 600)) for _ in range(8)]
        )
        for cliente in clientes:
            for _ in range(random.randint(1, 2)):
                matricula = self._matricula(usadas)
                modelo = random.choice(modelos)
                viatura = Viatura.objects.create(
                    cliente=cliente, local=random.choice(locais), matricula=matricula,
                    marca=modelo.marca, modelo=modelo,
                    ano=random.randint(2012, 2024),
                    combustivel=random.choice(COMBUSTIVEIS),
                    cor=random.choice(CORES),
                    inspecao_valida_ate=random.choice(ipo_opcoes))
                viaturas.append(viatura)
        self.stdout.write(f'  {len(viaturas)} viaturas.')
        return viaturas

    def _historico(self, viaturas, tipos, funcionarios, pecas):
        n_reg = 0
        pecas_por_servico = {
            'Mudança de óleo': [('OL-5W30', 4), ('FLT-OIL', 1)],
            'Revisão completa': [('OL-5W30', 5), ('FLT-OIL', 1), ('FLT-AIR', 1), ('FLT-CAB', 1)],
            'Travões — discos e pastilhas': [('BRK-PAD', 1), ('BRK-DISC', 2)],
            'Pneus & alinhamento': [('TIRE-205', 2)],
        }
        for viatura in viaturas:
            km = random.randint(20000, 80000)
            data = self.hoje - timedelta(days=random.randint(400, 900))
            func = random.choice(funcionarios)
            for _ in range(random.randint(1, 4)):
                tipo = random.choice(list(tipos.values()))
                km += random.randint(8000, 20000)
                data += timedelta(days=random.randint(120, 280))
                if data >= self.hoje:
                    data = self.hoje - timedelta(days=random.randint(1, 30))
                registo = RegistoServico.objects.create(
                    viatura=viatura, local=viatura.local, funcionario=func,
                    tipo_servico=tipo, data_servico=data, quilometragem=km,
                    trabalho_feito=f'{tipo.nome} efetuado. Tudo verificado e OK.',
                    estado=RegistoServico.Estado.CONCLUIDO,
                    registado_por=func.user)
                for ref, qtd in pecas_por_servico.get(tipo.nome, []):
                    peca = pecas[ref]
                    PecaServico.objects.create(
                        registo=registo, peca=peca, descricao=peca.nome,
                        quantidade=Decimal(qtd), preco_unitario=peca.preco_venda)
                n_reg += 1
        self.stdout.write(f'  {n_reg} registos de serviço (com peças).')

    def _inspecoes(self, viaturas, funcionarios):
        n = 0
        for viatura in random.sample(viaturas, min(6, len(viaturas))):
            estados_item = [ItemInspecao.Estado.OK] * 7 + [ItemInspecao.Estado.ATENCAO, ItemInspecao.Estado.URGENTE]
            piores = []
            insp = Inspecao.objects.create(
                viatura=viatura, local=viatura.local, funcionario=random.choice(funcionarios),
                data=self.hoje - timedelta(days=random.randint(0, 60)),
                quilometragem=viatura.quilometragem_atual or random.randint(30000, 120000),
                notas='Check-list realizado na receção da viatura.')
            for ponto in PONTOS_INSPECAO:
                estado = random.choice(estados_item)
                piores.append(estado)
                ItemInspecao.objects.create(
                    inspecao=insp, ponto=ponto, estado=estado,
                    nota='' if estado == ItemInspecao.Estado.OK else 'Verificar / substituir.')
            if ItemInspecao.Estado.URGENTE in piores:
                insp.resultado = Inspecao.Resultado.URGENTE
            elif ItemInspecao.Estado.ATENCAO in piores:
                insp.resultado = Inspecao.Resultado.ATENCAO
            insp.save(update_fields=['resultado'])
            n += 1
        self.stdout.write(f'  {n} inspeções (com check-list).')

    def _orcamentos(self, viaturas, tipos, funcionarios, pecas):
        n_total, n_aprovados = 0, 0
        for viatura in random.sample(viaturas, min(8, len(viaturas))):
            tipo = random.choice(list(tipos.values()))
            estado = random.choice([
                Orcamento.Estado.RASCUNHO, Orcamento.Estado.ENVIADO,
                Orcamento.Estado.ENVIADO, Orcamento.Estado.APROVADO])
            orc = Orcamento.objects.create(
                cliente=viatura.cliente, viatura=viatura, local=viatura.local,
                tipo_servico=tipo, funcionario=random.choice(funcionarios),
                estado=Orcamento.Estado.RASCUNHO,
                validade=self.hoje + timedelta(days=15),
                notas='Orçamento sem compromisso.')
            ItemOrcamento.objects.create(
                orcamento=orc, tipo=ItemOrcamento.Tipo.MAO_OBRA,
                descricao=f'Mão de obra — {tipo.nome}', quantidade=Decimal('1'),
                preco_unitario=tipo.preco_base or Decimal('50'))
            for ref in random.sample(list(pecas), random.randint(1, 3)):
                peca = pecas[ref]
                ItemOrcamento.objects.create(
                    orcamento=orc, tipo=ItemOrcamento.Tipo.PECA, peca=peca,
                    descricao=peca.nome, quantidade=Decimal(random.randint(1, 4)),
                    preco_unitario=peca.preco_venda)
            if estado == Orcamento.Estado.APROVADO:
                orc.aprovar(user=funcionarios[0].user)
                n_aprovados += 1
            else:
                orc.estado = estado
                orc.save(update_fields=['estado'])
            n_total += 1
        self.stdout.write(f'  {n_total} orçamentos ({n_aprovados} aprovados → geraram registo).')

    def _marcacoes(self, viaturas, tipos, funcionarios):
        n = 0
        base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        for viatura in random.sample(viaturas, min(7, len(viaturas))):
            quando = base + timedelta(days=random.randint(1, 21), hours=random.choice([0, 1, 2, 5, 6]))
            Marcacao.objects.create(
                cliente=viatura.cliente, viatura=viatura, local=viatura.local,
                tipo_servico=random.choice(list(tipos.values())),
                funcionario=random.choice(funcionarios), data_hora=quando,
                estado=random.choice([Marcacao.Estado.PENDENTE, Marcacao.Estado.CONFIRMADA]),
                notas='')
            n += 1
        self.stdout.write(f'  {n} marcações futuras.')

    def _ordens(self, viaturas, tipos, funcionarios, pecas):
        n = 0
        for i, viatura in enumerate(random.sample(viaturas, min(4, len(viaturas)))):
            func = random.choice(funcionarios)
            ordem = OrdemTrabalho.objects.create(
                viatura=viatura, local=viatura.local, funcionario=func,
                tipo_servico=random.choice(list(tipos.values())),
                quilometragem=viatura.quilometragem_atual or random.randint(40000, 150000),
                notas='Trabalho de demonstração.')
            inicio = timezone.now() - timedelta(hours=random.randint(3, 7))
            SessaoTrabalho.objects.create(
                ordem=ordem, funcionario=func, inicio=inicio,
                fim=inicio + timedelta(minutes=random.randint(45, 150)))
            if i == 0:
                # uma fica a decorrer (sessão aberta) -> em execução
                SessaoTrabalho.objects.create(
                    ordem=ordem, funcionario=func, inicio=timezone.now() - timedelta(minutes=25))
                ordem.estado = OrdemTrabalho.Estado.EM_EXECUCAO
            else:
                ordem.estado = OrdemTrabalho.Estado.PAUSADA
            ordem.save(update_fields=['estado'])
            for ref in random.sample(list(pecas), random.randint(1, 2)):
                peca = pecas[ref]
                ItemOrdem.objects.create(
                    ordem=ordem, tipo=ItemOrdem.Tipo.PECA, peca=peca, descricao=peca.nome,
                    quantidade=Decimal(random.randint(1, 2)), preco_unitario=peca.preco_venda,
                    fora_orcamento=True, nota='Imprevisto detetado durante o trabalho.')
            n += 1
        self.stdout.write(f'  {n} ordens de trabalho (tempo + extras).')

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _slug(texto):
        import re
        import unicodedata
        t = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
        t = re.sub(r'[^a-zA-Z0-9]+', '-', t).strip('-').lower()
        return t

    @staticmethod
    def _matricula(usadas):
        letras = 'ABCDEFGHJKLMNPRSTUVXZ'
        while True:
            m = f'{random.choice(letras)}{random.choice(letras)}-{random.randint(0, 99):02d}-{random.choice(letras)}{random.choice(letras)}'
            if m not in usadas:
                usadas.add(m)
                return m
