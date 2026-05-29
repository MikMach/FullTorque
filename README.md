# Full Torque

App de gestão para a oficina automóvel **Full Torque**. Começa com uma oficina,
mas está desenhada para escalar para uma **cadeia** (marcação online, escolha de local).

## Stack

- Python 3.12 + Django 5.2 LTS
- SQLite (local)
- HTMX + Tailwind (via CDN) no site público
- Django admin com tema **django-unfold** como painel de gestão (dono + funcionários)
- Identidade: logo/favicon em `static/img/`; paleta **vermelho + carvão** (tokens em `templates/base.html`, admin em `UNFOLD['COLORS']`)

## Correr localmente

Pré-requisito: **Python 3.12+** (no macOS: `brew install python@3.12`).

```bash
# 1. Ambiente + dependências
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Base de dados
python manage.py migrate

# 3. Conta de dono (admin) — interativo
python manage.py createsuperuser

# 4. Dados de demonstração (catálogo + operação)
python manage.py seed_demo            # cria se a BD estiver vazia
python manage.py seed_demo --reset    # apaga operação e recria

# 5. Arrancar
python manage.py runserver
```

- Site público: <http://127.0.0.1:8000/>
- Painel de gestão: <http://127.0.0.1:8000/admin/>

### Acessos (demo)
- **Dono** (vê tudo): `dono@fulltorque.pt` / `FullTorque2026`
- **Funcionários** (acesso simplificado): `joao@fulltorque.pt`, `maria@fulltorque.pt`,
  `pedro@fulltorque.pt` — password `demo12345`
- **Cliente** (portal em `/cliente/`): `cliente@fulltorque.pt` — password `demo12345`

> Troca estas credenciais antes de usar a sério.

## Papéis e acesso

- O **Dono** (superuser) vê tudo: catálogo, gestão e operação + dashboard com KPIs.
- O **Funcionário** (grupo de permissões "Funcionário") vê só a **Operação**
  (marcações, viaturas, registos, inspeções, orçamentos, clientes), pode consultar o
  catálogo mas **não o edita**, e não acede a utilizadores/locais.

## Modelo de domínio

- **Marca / Modelo** — catálogo de viaturas (seed com marcas/modelos populares em PT).
- **Local** — oficina/sucursal; tudo o que é operacional aponta para um local.
- **Cliente** — cliente da *marca* (sem local; servido em qualquer oficina).
- **Viatura** — viatura de um cliente (marca/modelo do catálogo, IPO, local de registo).
- **TipoServico** — catálogo de serviços; intervalos definem as próximas revisões.
- **Peca / StockPeca** — catálogo de peças + stock por local.
- **Funcionario** — funcionário de um local (com login opcional).
- **RegistoServico** — **append-only** (ver abaixo); peças por linha (**PecaServico**) e fotos.
- **Inspecao / ItemInspecao** — check-list digital (DVI) com pontos verificados e fotos.
- **Orcamento / ItemOrcamento** — orçamento → ao aprovar, **gera o RegistoServico**.
- **Marcacao** — agendamento (gerido no admin pelo staff).

### Decisões estruturais

- **Custom User desde o início**, login por email, com campo `papel`.
- **`local` em viaturas, funcionários, registos, marcações, inspeções, orçamentos** — pronto para a cadeia.
- **`RegistoServico` é append-only**: não se edita nem apaga (bloqueado no modelo e no
  admin). Correção = **nova entrada** ligada via `registo_corrigido`. Log auditável que
  protege o dono numa reclamação.
- **Próximas revisões e IPO** calculam-se a partir dos dados (lembretes no dashboard).

## Funcionalidades

- Catálogo de marcas/modelos e de peças com stock por local.
- Ciclo **orçamento → aprovação → registo de serviço** (ação no admin).
- **Inspeção digital** (check-list com estados ok/atenção/urgente e fotos).
- **Dashboard do dono** com KPIs e lembretes (IPO a vencer, orçamentos por aprovar).
- Admin com tema moderno (Unfold), simplificado por papel.
- **Marcação online** no site público (oficina → serviço → viatura → contactos), com HTMX.
- **Portal do cliente** (`/cliente/`): registo/login por email, as suas viaturas, histórico de
  serviços, próximas revisões/IPO e marcações.
- **Disponibilidade nas marcações**: cada oficina tem capacidade por horário (`Local.capacidade_slot`);
  horários cheios deixam de aparecer (HTMX) e são recusados na validação.
- **Notificações por email** ao criar marcação (confirmação ao cliente + alerta à oficina;
  consola em desenvolvimento, SMTP em produção).

## Ainda não feito (fases posteriores)

Faturação/PDF dos orçamentos; notificações por SMS; confirmação/lembrete automático das
marcações; tablet dedicado do funcionário; conteúdo real (morada, serviços).
