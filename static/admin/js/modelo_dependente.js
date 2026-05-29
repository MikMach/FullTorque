/* Filtro dependente Marca -> Modelo no admin.
 *
 * Ao escolher a Marca, a pesquisa (autocomplete) do campo Modelo passa a
 * devolver SÓ os modelos dessa marca. Funciona no formulário de Viatura e nos
 * inlines (várias viaturas no Cliente). Sem dependências: usa o jQuery/select2
 * que o admin já carrega. O backend filtra em ModeloAdmin.get_search_results.
 */
(function () {
    if (typeof django === 'undefined' || !django.jQuery) { return; }
    var $ = django.jQuery;

    function linha($el) {
        // O "contentor" da mesma viatura (linha de inline ou formulário principal).
        return $el.closest('.dynamic-viaturas, .inline-related, tr, .form-row, fieldset.module, form');
    }
    function marcaDe($modelo) {
        var $marca = linha($modelo)
            .find('select[name$="marca"], select[name="marca"], #id_marca').first();
        return $marca.val() || '';
    }

    var marcaAtual = '';

    // Quando um campo Modelo é aberto, fixa a marca da mesma linha.
    $(document).on('select2:opening', 'select[name$="modelo"], #id_modelo', function () {
        marcaAtual = marcaDe($(this));
    });

    // Acrescenta &marca=<id> ao pedido de autocomplete do campo Modelo.
    $(document).ajaxSend(function (event, jqxhr, settings) {
        if (marcaAtual && settings.url && settings.url.indexOf('field_name=modelo') !== -1) {
            settings.url += (settings.url.indexOf('?') !== -1 ? '&' : '?')
                + 'marca=' + encodeURIComponent(marcaAtual);
        }
    });

    // Ao mudar a Marca, limpa o Modelo da mesma linha (evita pares trocados).
    $(document).on('change', 'select[name$="marca"], #id_marca', function () {
        var $modelo = linha($(this)).find('select[name$="modelo"], #id_modelo').first();
        if ($modelo.length) { $modelo.val(null).trigger('change'); }
    });
})();
