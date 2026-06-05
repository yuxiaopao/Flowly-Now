/**
 * e-Flowly Admin — Dynamic Interaction Layer
 */

(function() {
    'use strict';

    // ── Keyboard shortcuts ──
    $(document).on('keydown', function(e) {
        // Ctrl+S — save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            var $form = $('form:visible').last();
            if ($form.length) $form.find('[type="submit"]').first().click();
        }
        // Ctrl+/ — focus search
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            var $search = $('#searchbar, .f-input, input[type="text"]').first();
            if ($search.length) { $search.focus().select(); }
        }
    });

    // ── Form submit feedback ──
    $('form').on('submit', function() {
        var $btn = $(this).find('[type="submit"]');
        if ($btn.length) {
            $btn.prop('disabled', true).css('opacity', '0.7');
            $btn.html('<i class="fas fa-spinner fa-spin"></i> 保存中...');
        }
    });

    // ── Danger action confirmation ──
    $(document).on('click', 'a[href*="delete"], a.action-delete, button[name="_save"].btn-outline-danger', function(e) {
        var text = $(this).attr('title') || $(this).text().trim() || '此操作';
        if (text && text !== '删除' && text !== 'Delete' && text !== '删除 selected') {
            if (!confirm('⚠️ 确定要 ' + text + ' 吗？此操作不可撤销！')) {
                e.preventDefault();
                return false;
            }
        }
    });

    // ── Toast for Django messages ──
    $('.messages li').each(function() {
        var $msg = $(this);
        var text = $msg.text().trim();
        var type = 'info';
        if ($msg.hasClass('success')) type = 'success';
        else if ($msg.hasClass('error')) type = 'error';
        else if ($msg.hasClass('warning')) type = 'warning';
        if (window.showToast) window.showToast(text, type);
        $msg.remove();
    });

    // ── Auto-resize textareas ──
    $('textarea').each(function() {
        this.style.resize = 'vertical';
        this.style.minHeight = '80px';
    });

    // ── Copy to clipboard ──
    $(document).on('click', '[data-copy]', function() {
        var text = $(this).data('copy');
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(function() {
                if (window.showToast) window.showToast('已复制: ' + text, 'success');
            }).catch(function() {
                if (window.showToast) window.showToast('复制失败', 'error');
            });
        }
    });

    // ── Jazzmin related lookup button enhancement ──
    $('.related-widget-wrapper select').on('change', function() {
        var $addBtn = $(this).closest('.related-widget-wrapper').find('.add-another, .related-lookup');
        if ($addBtn.length) $addBtn.css('opacity', 1);
    });

})();
