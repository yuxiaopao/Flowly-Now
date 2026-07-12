/**
 * Flowly Admin — Dynamic Interaction Layer
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
    $(document).on('click', 'a[href*="/delete/"], a.deletelink, .deletelink-box a', function(e) {
        if (!confirm('确定要删除吗？此操作不可撤销。')) {
            e.preventDefault();
            return false;
        }
    });

    $(document).on('submit', '#changelist-form', function(e) {
        var action = $(this).find('select[name="action"]').val();
        if (action && action.indexOf('delete') !== -1) {
            if (!confirm('确定要对所选记录执行批量删除吗？此操作不可撤销。')) {
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

    // ── Sidebar: 分组独立展开/收起（与 AdminLTE 解耦，防重复绑定） ──
    $(function initFlowlySidebar() {
        if (window.__flowlySidebarInit) return;
        window.__flowlySidebarInit = true;

        var STORAGE_KEY = 'flowly_sidebar_open_groups_v2';
        var $sidebar = $('.nav-sidebar[data-widget="treeview"]');
        if (!$sidebar.length) return;

        // 禁用 AdminLTE Treeview 插件，避免与 Flowly 双击切换冲突
        $sidebar.removeAttr('data-widget');

        function groupKey($item) {
            var label = $.trim(
                $item.children('.nav-link').find('p').first().clone().children().remove().end().text()
            );
            return label || ('group-' + $item.index());
        }

        function readOpenGroups() {
            try {
                var raw = localStorage.getItem(STORAGE_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                return [];
            }
        }

        function writeOpenGroups(keys) {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
            } catch (e) { /* ignore quota */ }
        }

        function setOpen($item, open) {
            $item.toggleClass('menu-is-opening menu-open', !!open);
            $item.children('.nav-treeview').css('display', open ? 'block' : 'none');
        }

        function collectOpenKeys() {
            return $sidebar.children('.nav-item.has-treeview.menu-open').map(function() {
                return groupKey($(this));
            }).get();
        }

        function collapseAll() {
            $sidebar.children('.nav-item.has-treeview').each(function() {
                setOpen($(this), false);
            });
        }

        function expandAll() {
            $sidebar.children('.nav-item.has-treeview').each(function() {
                setOpen($(this), true);
            });
        }

        function applyInitialState() {
            var saved = readOpenGroups();
            collapseAll();

            $sidebar.children('.nav-item.has-treeview').each(function() {
                var $item = $(this);
                var key = groupKey($item);
                var hasActiveChild = $item.find('.nav-link.active').length > 0;
                if (hasActiveChild || $.inArray(key, saved) !== -1) {
                    setOpen($item, true);
                }
            });
        }

        if (!$sidebar.prev('.flowly-sidebar-tools').length) {
            var $tools = $(
                '<div class="flowly-sidebar-tools" role="group" aria-label="侧边栏菜单控制">' +
                '<button type="button" class="flowly-sidebar-tool" data-action="expand-all">全部展开</button>' +
                '<button type="button" class="flowly-sidebar-tool" data-action="collapse-all">全部收起</button>' +
                '</div>'
            );
            $sidebar.before($tools);

            $tools.on('click', '[data-action="expand-all"]', function(e) {
                e.preventDefault();
                expandAll();
                writeOpenGroups(collectOpenKeys());
            });

            $tools.on('click', '[data-action="collapse-all"]', function(e) {
                e.preventDefault();
                collapseAll();
                writeOpenGroups([]);
            });
        }

        $sidebar.off('click.flowlyTree', '.nav-item.has-treeview > .nav-link');
        $sidebar.on('click.flowlyTree', '.nav-item.has-treeview > .nav-link', function(e) {
            e.preventDefault();
            e.stopPropagation();
            var $item = $(this).closest('.nav-item.has-treeview');
            setOpen($item, !$item.hasClass('menu-open'));
            writeOpenGroups(collectOpenKeys());
        });

        // 在 Jazzmin setActiveLinks 之后应用初始状态
        setTimeout(function() {
            applyInitialState();
            writeOpenGroups(collectOpenKeys());
        }, 50);

        $(window).on('beforeunload.flowlySidebar', function() {
            writeOpenGroups(collectOpenKeys());
        });
    });

})();
