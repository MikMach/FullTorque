"""Registo dos modelos sincronizados, direção e campos.

Direção (na perspetiva do servidor LOCAL/oficina):
- 'up'   : a oficina é a fonte → envia para a cloud.
- 'down' : a cloud é a fonte → a oficina puxa.
- 'both' : criado/alterado dos dois lados → last-write-wins por `atualizado_em`.

A ORDEM importa: dependências (pais) primeiro, para resolver as FKs por uuid.
"""
from oficina import models as m

# (Modelo, direcao, campos_escalares, fks {campo: Modelo})
REGISTO = [
    (m.Local, 'up', ['nome', 'morada', 'codigo_postal', 'cidade', 'telefone', 'email', 'slug', 'capacidade_slot', 'ativo'], {}),
    (m.Marca, 'up', ['nome', 'slug', 'ativo'], {}),
    (m.Modelo, 'up', ['nome', 'ativo'], {'marca': m.Marca}),
    (m.TipoServico, 'up', ['nome', 'descricao', 'preco_base', 'duracao_estimada', 'intervalo_km', 'intervalo_meses', 'ativo'], {}),
    (m.Peca, 'up', ['referencia', 'nome', 'preco_venda', 'ativo'], {}),
    (m.Funcionario, 'up', ['nome', 'telefone', 'cargo', 'ativo', 'data_admissao'], {'local': m.Local}),
    (m.Cliente, 'both', ['nome', 'telefone', 'email', 'nif', 'morada'], {}),
    (m.Viatura, 'both', ['matricula', 'ano', 'combustivel', 'cor', 'vin', 'inspecao_valida_ate'],
     {'cliente': m.Cliente, 'local': m.Local, 'marca': m.Marca, 'modelo': m.Modelo}),
    (m.RegistoServico, 'up', ['data_servico', 'quilometragem', 'trabalho_feito', 'estado', 'criado_em'],
     {'viatura': m.Viatura, 'local': m.Local, 'funcionario': m.Funcionario, 'tipo_servico': m.TipoServico}),
    (m.PecaServico, 'up', ['descricao', 'quantidade', 'preco_unitario'], {'registo': m.RegistoServico, 'peca': m.Peca}),
    (m.OrdemTrabalho, 'up', ['estado', 'quilometragem', 'notas', 'criado_em', 'concluida_em'],
     {'viatura': m.Viatura, 'local': m.Local, 'tipo_servico': m.TipoServico, 'funcionario': m.Funcionario}),
    (m.ItemOrdem, 'up', ['tipo', 'descricao', 'quantidade', 'preco_unitario', 'fora_orcamento', 'nota'],
     {'ordem': m.OrdemTrabalho, 'peca': m.Peca}),
    (m.Inspecao, 'up', ['data', 'quilometragem', 'resultado', 'notas'],
     {'viatura': m.Viatura, 'local': m.Local, 'funcionario': m.Funcionario}),
    (m.ItemInspecao, 'up', ['ponto', 'estado', 'nota'], {'inspecao': m.Inspecao}),
    (m.Marcacao, 'down', ['data_hora', 'estado', 'notas', 'criado_em'],
     {'cliente': m.Cliente, 'viatura': m.Viatura, 'local': m.Local, 'tipo_servico': m.TipoServico, 'funcionario': m.Funcionario}),
]
