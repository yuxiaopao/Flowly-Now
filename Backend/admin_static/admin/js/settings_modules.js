/**
 * Flowly Admin — Platform Settings Hub
 */
(function(global) {
    'use strict';

    var MODULE_ICONS = {
        general: 'fa-globe',
        terms: 'fa-file-contract',
        features: 'fa-sliders-h',
        security: 'fa-shield-alt',
        user_defaults: 'fa-user-cog',
        gateway: 'fa-network-wired',
        payment: 'fa-credit-card',
        email: 'fa-envelope',
        backup: 'fa-database',
    };

    var CRUD_MODULES = {
        terms: {
            title: '法律文档',
            endpoint: '/api/v1/admin/legal-documents/',
            columns: ['doc_type', 'version', 'title', 'is_active', 'acceptance_count'],
            formFields: [
                { key: 'doc_type', label: '文档类型', type: 'choice', choices: [
                    { value: 'terms', label: '服务条款' },
                    { value: 'privacy', label: '隐私政策' },
                    { value: 'login', label: '登录协议' },
                ]},
                { key: 'version', label: '版本号', type: 'string' },
                { key: 'title', label: '标题', type: 'string' },
                { key: 'content_html', label: 'HTML 内容', type: 'textarea' },
                { key: 'is_active', label: '当前生效', type: 'boolean' },
                { key: 'require_acceptance', label: '注册需确认', type: 'boolean' },
            ],
            extraList: '/api/v1/admin/terms-acceptances/',
            extraListTitle: '用户确认记录',
        },
        features: {
            title: '功能可见性规则',
            endpoint: '/api/v1/admin/feature-visibility/',
            columns: ['feature_key', 'scope', 'role', 'is_visible', 'is_enabled'],
            formFields: [
                { key: 'feature_key', label: '功能标识', type: 'string' },
                { key: 'scope', label: '作用范围', type: 'choice', choices: [
                    { value: 'global', label: '全局' },
                    { value: 'role', label: '用户角色' },
                    { value: 'group', label: '用户组' },
                ]},
                { key: 'role', label: '角色', type: 'string' },
                { key: 'is_visible', label: '可见', type: 'boolean' },
                { key: 'is_enabled', label: '启用', type: 'boolean' },
            ],
        },
        gateway: {
            title: '网关路由规则',
            endpoint: '/api/v1/admin/gateway-routes/',
            columns: ['name', 'path_pattern', 'target_service', 'rate_limit_per_minute', 'is_enabled'],
            formFields: [
                { key: 'name', label: '规则名称', type: 'string' },
                { key: 'path_pattern', label: '路径匹配', type: 'string' },
                { key: 'target_service', label: '目标服务', type: 'string' },
                { key: 'methods', label: 'HTTP 方法(JSON数组)', type: 'string', default: '["GET","POST"]' },
                { key: 'rate_limit_per_minute', label: '限流(次/分)', type: 'integer' },
                { key: 'priority', label: '优先级', type: 'integer' },
                { key: 'is_enabled', label: '启用', type: 'boolean' },
            ],
        },
        payment: {
            title: '支付渠道',
            endpoint: '/api/v1/admin/payment-providers/',
            columns: ['provider', 'display_name', 'is_enabled', 'fee_rate'],
            formFields: [
                { key: 'provider', label: '渠道', type: 'choice', choices: [
                    { value: 'stripe', label: 'Stripe' },
                    { value: 'alipay', label: '支付宝' },
                    { value: 'wechat', label: '微信支付' },
                    { value: 'paypal', label: 'PayPal' },
                ]},
                { key: 'display_name', label: '显示名称', type: 'string' },
                { key: 'is_enabled', label: '启用', type: 'boolean' },
                { key: 'fee_rate', label: '费率', type: 'string' },
                { key: 'config', label: '配置(JSON)', type: 'textarea', default: '{}' },
            ],
        },
        email: {
            title: '邮件发送记录',
            endpoint: '/api/v1/admin/email-logs/',
            columns: ['to_email', 'subject', 'status', 'sent_at'],
            readOnly: true,
            testEmail: true,
        },
        backup: {
            title: '备份记录',
            endpoint: '/api/v1/admin/backup-records/',
            columns: ['name', 'backup_type', 'size', 'status', 'created_at'],
            readOnly: true,
            backupActions: true,
        },
    };

    var hub = {
        currentModule: 'general',
        modules: [],
        isDirty: false,
        _dirtyBound: false,

        init: async function(module) {
            this.currentModule = module;
            window.addEventListener('popstate', function(e) {
                var m = (e.state && e.state.module) || new URLSearchParams(window.location.search).get('module') || 'general';
                if (m !== hub.currentModule) {
                    hub.isDirty = false;
                    hub.switchModule(m, true);
                }
            });
            await this.loadModules();
            this.renderNav();
            await this.loadModule(module);
        },

        bindDirtyTracking: function() {
            var area = document.getElementById('settingsFormArea');
            if (!area || this._dirtyBound) return;
            this._dirtyBound = true;
            var markDirty = function() { hub.isDirty = true; };
            area.addEventListener('change', markDirty, true);
            area.addEventListener('input', markDirty, true);
            window.addEventListener('beforeunload', function(e) {
                if (hub.isDirty) {
                    e.preventDefault();
                    e.returnValue = '';
                }
            });
        },

        moduleHintHtml: function(module) {
            if (module === 'features') {
                return '<div class="settings-module-hint"><i class="fas fa-info-circle" aria-hidden="true"></i> ' +
                    '此处管理按角色/范围的功能<strong>可见性规则</strong>。运行时开关请前往 ' +
                    '<a href="/admin/flowly/features/">功能开关 Tab</a>。</div>';
            }
            return '';
        },

        loadModules: async function() {
            var data = await apiCall('/api/v1/admin/settings/modules/');
            this.modules = data.modules || [];
        },

        renderNav: function() {
            var nav = document.getElementById('settingsNav');
            nav.innerHTML = this.modules.map(function(m) {
                var icon = MODULE_ICONS[m.id] || 'fa-cog';
                var active = m.id === hub.currentModule ? ' active' : '';
                return '<button type="button" class="settings-nav-item' + active + '" data-module="' + m.id + '" onclick="SettingsHub.switchModule(\'' + m.id + '\')">' +
                    '<i class="fas ' + icon + '"></i> ' + m.label + '</button>';
            }).join('');
        },

        switchModule: async function(module, skipHistory) {
            if (!skipHistory && this.isDirty && module !== this.currentModule) {
                if (!confirm('有未保存的修改，确定切换模块吗？')) return;
            }
            this.isDirty = false;
            this.currentModule = module;
            if (!skipHistory) {
                history.pushState({ module: module }, '', '?module=' + encodeURIComponent(module));
            }
            this.renderNav();
            await this.loadModule(module);
        },

        loadModule: async function(module) {
            showLoading();
            this.isDirty = false;
            try {
                var data = await apiCall('/api/v1/admin/settings/modules/' + module + '/');
                document.getElementById('settingsModuleTitle').textContent = data.label || module;
                this.renderForm(data.schema || [], module);
                await this.renderCrud(module);
            } catch(e) {
                showToast('加载模块失败', 'error');
            }
            hideLoading();
        },

        renderForm: function(schema, module) {
            var area = document.getElementById('settingsFormArea');
            if (!schema.length) {
                area.innerHTML = this.moduleHintHtml(module) + '<div class="f-empty"><p>此模块无键值配置项</p></div>';
                return;
            }
            var html = '<div class="settings-form-grid">';
            schema.forEach(function(field) {
                html += '<div class="settings-field"><label for="sf_' + field.key + '">' + field.label + '</label>';
                if (field.type === 'boolean') {
                    html += '<label class="f-toggle"><input type="checkbox" id="sf_' + field.key + '" ' +
                        (field.value ? 'checked' : '') + ' aria-label="' + field.label + '"><span class="f-toggle-track"></span></label>';
                } else if (field.type === 'choice') {
                    html += '<select id="sf_' + field.key + '" class="f-input f-select">';
                    (field.choices || []).forEach(function(c) {
                        html += '<option value="' + c + '"' + (field.value === c ? ' selected' : '') + '>' + c + '</option>';
                    });
                    html += '</select>';
                } else {
                    var inputType = field.type === 'integer' ? 'number' : 'text';
                    html += '<input type="' + inputType + '" id="sf_' + field.key + '" class="f-input" value="' +
                        (field.value != null ? String(field.value).replace(/"/g, '&quot;') : '') + '">';
                }
                html += '</div>';
            });
            html += '</div><div class="settings-actions"><button class="f-btn f-btn-primary" onclick="SettingsHub.saveModule(\'' + module + '\')"><i class="fas fa-save"></i> 保存配置</button></div>';
            area.innerHTML = this.moduleHintHtml(module) + html;
            this.bindDirtyTracking();
        },

        saveModule: async function(module) {
            var data = await apiCall('/api/v1/admin/settings/modules/' + module + '/');
            var payload = {};
            (data.schema || []).forEach(function(field) {
                var el = document.getElementById('sf_' + field.key);
                if (!el) return;
                if (field.type === 'boolean') payload[field.key] = el.checked;
                else if (field.type === 'integer') payload[field.key] = parseInt(el.value, 10) || 0;
                else payload[field.key] = el.value;
            });
            try {
                await apiCall('/api/v1/admin/settings/modules/' + module + '/', 'PATCH', payload);
                this.isDirty = false;
                showToast('配置已保存并同步', 'success');
            } catch(e) {
                showToast('保存失败', 'error');
            }
        },

        renderCrud: async function(module) {
            var area = document.getElementById('settingsCrudArea');
            var cfg = CRUD_MODULES[module];
            if (!cfg) { area.innerHTML = ''; return; }

            var html = '<div class="settings-toolbar"><div class="settings-subtitle">' + cfg.title + '</div>';
            if (!cfg.readOnly) {
                html += '<button class="f-btn f-btn-primary f-btn-sm" onclick="SettingsHub.openCreate(\'' + module + '\')"><i class="fas fa-plus"></i> 新建</button>';
            }
            if (cfg.testEmail) {
                html += '<button class="f-btn f-btn-sm" onclick="SettingsHub.testEmail()"><i class="fas fa-paper-plane"></i> 测试邮件</button>';
            }
            if (cfg.backupActions) {
                html += '<button class="f-btn f-btn-sm" onclick="SettingsHub.createBackup()"><i class="fas fa-download"></i> 立即备份</button>';
            }
            html += '</div><div id="crudTableWrap" class="settings-table-wrap">加载中...</div>';
            area.innerHTML = html;

            try {
                var list = await apiCall(cfg.endpoint);
                var items = list.results || list;
                if (!Array.isArray(items)) items = [];
                this.renderTable(module, items, cfg);
                if (cfg.extraList) this.loadExtraList(cfg);
            } catch(e) {
                document.getElementById('crudTableWrap').innerHTML = '<div class="f-empty">加载失败</div>';
            }
        },

        renderTable: function(module, items, cfg) {
            var wrap = document.getElementById('crudTableWrap');
            if (!items.length) {
                wrap.innerHTML = '<div class="f-empty"><p>暂无数据</p></div>';
                return;
            }
            var html = '<table class="f-table"><thead><tr>';
            cfg.columns.forEach(function(c) { html += '<th>' + c + '</th>'; });
            if (!cfg.readOnly) html += '<th>操作</th>';
            else if (cfg.backupActions) html += '<th>操作</th>';
            html += '</tr></thead><tbody>';
            items.forEach(function(item) {
                html += '<tr>';
                cfg.columns.forEach(function(c) {
                    var val = item[c];
                    if (typeof val === 'boolean') val = val ? '是' : '否';
                    html += '<td>' + (val != null ? val : '—') + '</td>';
                });
                if (!cfg.readOnly) {
                    html += '<td><button class="f-btn f-btn-sm f-btn-ghost" onclick="SettingsHub.deleteItem(\'' + module + '\',' + item.id + ')">删除</button></td>';
                } else if (cfg.backupActions && item.id) {
                    html += '<td><button class="f-btn f-btn-sm f-btn-ghost" onclick="SettingsHub.downloadBackup(' + item.id + ')">下载</button></td>';
                }
                html += '</tr>';
            });
            html += '</tbody></table>';
            wrap.innerHTML = html;
        },

        openCreate: function(module) {
            var cfg = CRUD_MODULES[module];
            if (!cfg) return;
            var body = cfg.formFields.map(function(f) {
                var val = f.default || '';
                if (f.type === 'boolean') {
                    return '<div class="settings-field"><label>' + f.label + '</label><input type="checkbox" id="nc_' + f.key + '"></div>';
                }
                if (f.type === 'choice') {
                    var opts = f.choices.map(function(c) {
                        return '<option value="' + c.value + '">' + c.label + '</option>';
                    }).join('');
                    return '<div class="settings-field"><label>' + f.label + '</label><select id="nc_' + f.key + '" class="f-input">' + opts + '</select></div>';
                }
                if (f.type === 'textarea') {
                    return '<div class="settings-field"><label>' + f.label + '</label><textarea id="nc_' + f.key + '" class="f-input" rows="4">' + val + '</textarea></div>';
                }
                return '<div class="settings-field"><label>' + f.label + '</label><input id="nc_' + f.key + '" class="f-input" value="' + val + '"></div>';
            }).join('');

            var modal = document.createElement('div');
            modal.className = 'f-modal-overlay';
            modal.innerHTML = '<div class="f-modal"><div class="f-modal-header"><h3>新建 ' + cfg.title + '</h3>' +
                '<button class="f-modal-close" onclick="this.closest(\'.f-modal-overlay\').remove()">&#x2715;</button></div>' +
                body + '<div class="settings-actions"><button class="f-btn f-btn-primary" id="ncSave">保存</button></div></div>';
            document.body.appendChild(modal);
            document.getElementById('ncSave').onclick = function() { hub.submitCreate(module, modal); };
        },

        submitCreate: async function(module, modal) {
            var cfg = CRUD_MODULES[module];
            var payload = {};
            cfg.formFields.forEach(function(f) {
                var el = document.getElementById('nc_' + f.key);
                if (!el) return;
                if (f.type === 'boolean') payload[f.key] = el.checked;
                else if (f.key === 'methods') {
                    try { payload[f.key] = JSON.parse(el.value); } catch(e) { payload[f.key] = ['GET']; }
                } else if (f.key === 'config') {
                    try { payload[f.key] = JSON.parse(el.value); } catch(e) { payload[f.key] = {}; }
                } else if (f.type === 'integer') payload[f.key] = parseInt(el.value, 10) || 0;
                else payload[f.key] = el.value;
            });
            try {
                await apiCall(cfg.endpoint, 'POST', payload);
                modal.remove();
                showToast('创建成功', 'success');
                await hub.renderCrud(module);
            } catch(e) {
                showToast('创建失败', 'error');
            }
        },

        deleteItem: async function(module, id) {
            if (!confirm('确定删除？')) return;
            var cfg = CRUD_MODULES[module];
            try {
                await apiCall(cfg.endpoint + id + '/', 'DELETE');
                showToast('已删除', 'success');
                await hub.renderCrud(module);
            } catch(e) {
                showToast('删除失败', 'error');
            }
        },

        testEmail: async function() {
            var email = prompt('测试收件邮箱：');
            if (!email) return;
            try {
                await apiCall('/api/v1/admin/email/test/', 'POST', { to_email: email });
                showToast('测试邮件已发送', 'success');
                await hub.renderCrud('email');
            } catch(e) {
                showToast('发送失败', 'error');
            }
        },

        createBackup: async function() {
            try {
                await apiCall('/api/v1/admin/backup/', 'POST', { type: 'full', include_media: true });
                showToast('备份任务已完成', 'success');
                await hub.renderCrud('backup');
            } catch(e) {
                showToast('备份失败', 'error');
            }
        },

        downloadBackup: function(id) {
            window.open('/api/v1/admin/backup-records/' + id + '/download/', '_blank', 'noopener,noreferrer');
        },

        loadExtraList: async function(cfg) {
            try {
                var list = await apiCall(cfg.extraList);
                var items = list.results || list;
                if (!Array.isArray(items) || !items.length) return;
                var area = document.getElementById('settingsCrudArea');
                var html = '<div class="settings-subtitle" style="margin-top:24px">' + cfg.extraListTitle + '</div>';
                html += '<table class="f-table"><thead><tr><th>用户</th><th>文档</th><th>版本</th><th>时间</th></tr></thead><tbody>';
                items.slice(0, 20).forEach(function(item) {
                    html += '<tr><td>' + (item.username || item.user) + '</td><td>' + (item.document_title || item.document) +
                        '</td><td>' + item.document_version + '</td><td>' + (item.accepted_at || '') + '</td></tr>';
                });
                html += '</tbody></table>';
                area.innerHTML += html;
            } catch(e) { /* ignore */ }
        },

        refresh: function() {
            this.loadModule(this.currentModule);
        },
    };

    global.SettingsHub = hub;
})(window);
