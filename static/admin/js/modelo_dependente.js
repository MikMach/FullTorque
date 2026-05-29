/* Filtro dependente Marca -> Modelo no admin.
 *
 * Ao escolher a Marca, a pesquisa (autocomplete) do campo Modelo passa a
 * devolver SÓ os modelos dessa marca. Funciona no formulário de Viatura e nos
 * inlines (várias viaturas no Cliente). Backend: ModeloAdmin.get_search_results.
 *
 * Lições aprendidas (porque versões anteriores falhavam):
 *  1) o admin inclui este ficheiro ANTES do jquery.init.js -> esperar DOMContentLoaded;
 *  2) os eventos do select2 NÃO borbulham até ao document -> ligar select2:opening
 *     DIRETAMENTE em cada <select> de modelo;
 *  3) no form principal, marca e modelo estão em linhas/divs SEPARADAS, por isso
 *     a marca descobre-se pelo NOME do campo (viaturas-0-modelo -> viaturas-0-marca;
 *     ou #id_marca no form principal), não andando pelo DOM à volta;
 *  4) injetar a marca via $.ajaxPrefilter (altera o pedido antes de o URL ser montado).
 */
(function () {
    function init() {
        if (typeof django === 'undefined' || !django.jQuery) { return; }
        var $ = django.jQuery;

        // Seletor da marca correspondente a um campo de modelo (e vice-versa),
        // a partir do nome: inline "viaturas-0-modelo" <-> "viaturas-0-marca".
        function irmaoSelector(name, de, para) {
            var re = new RegExp('^(.*-)' + de + '$');
            var m = (name || '').match(re);
            if (m) { return 'select[name="' + m[1] + para + '"]'; }
            return 'select[name="' + para + '"], #id_' + para;
        }
        function valorMarcaDe($modelo) {
            var sel = irmaoSelector($modelo.attr('name'), 'modelo', 'marca');
            return $modelo.closest('form').find(sel).first().val() || '';
        }

        var marcaAtual = '';

        function ligaModelos() {
            $('select[name$="modelo"]').each(function () {
                var $m = $(this), name = $m.attr('name') || '';
                if ($m.data('mdepBound') || name.indexOf('__prefix__') !== -1) { return; }
                $m.data('mdepBound', true);
                $m.on('select2:opening', function () { marcaAtual = valorMarcaDe($m); });
            });
        }
        ligaModelos();
        $(document).on('formset:added', ligaModelos);  // novas linhas de inline

        // Acrescenta a marca aos dados do pedido (o jQuery serializa `data` para
        // o URL DEPOIS dos prefilters, por isso isto é fiável).
        $.ajaxPrefilter(function (options) {
            if (!marcaAtual || !options || typeof options.data !== 'string') { return; }
            if ((options.url || '').indexOf('/autocomplete/') === -1) { return; }
            if (options.data.indexOf('field_name=modelo') === -1) { return; }
            if (options.data.indexOf('marca=') !== -1) { return; }
            options.data += '&marca=' + encodeURIComponent(marcaAtual);
        });

        // Ao mudar a Marca, limpa o Modelo correspondente (evita pares trocados).
        function ligaMarcas() {
            $('select[name$="marca"]').each(function () {
                var $marca = $(this), name = $marca.attr('name') || '';
                if ($marca.data('mdepMarca') || name.indexOf('__prefix__') !== -1) { return; }
                $marca.data('mdepMarca', true);
                $marca.on('change', function () {
                    var sel = irmaoSelector(name, 'marca', 'modelo');
                    var $m = $marca.closest('form').find(sel).first();
                    if ($m.length) { $m.val(null).trigger('change'); }
                });
            });
        }
        ligaMarcas();
        $(document).on('formset:added', ligaMarcas);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
