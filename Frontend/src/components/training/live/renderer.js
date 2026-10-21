export function mountTrainingMonitor(root, api) {
const $ = id => root.getElementById(id);
const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const number = value => Number.isFinite(value) ? value.toLocaleString('zh-CN') : '—';
const decimal = (value, digits = 4) => Number.isFinite(value) ? value.toFixed(digits) : '—';
const percent = value => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : '—';
const clock = value => value ? new Date(value).toLocaleTimeString('zh-CN', { hour12: false }) : '—';
const duration = value => {
  if (!Number.isFinite(value)) return '估算中';
  const seconds = Math.max(0, Math.round(value));
  return seconds >= 3600 ? `${Math.floor(seconds / 3600)} 小时 ${Math.floor(seconds % 3600 / 60)} 分`
    : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`;
};
const STAGES = {
  training: '正在训练', evaluating_val: '评估完整验证集', evaluating_test: '评估独立测试集',
  exporting: '导出模型与一致性校验', ready_for_system_test: '模型已训练 · 等待系统验收',
  quality_gate_failed: '验证门槛未通过', failed: '训练流程失败', interrupted: '训练进程已中断',
  completed: '训练与验收已完成',
};
const PARAMETERS = {
  epochs: '最大轮次', patience: '提前停止耐心轮数', imgsz: '输入图像尺寸', batch: '批量大小',
  workers: '数据加载进程数', device: '训练设备', seed: '随机种子', lr0: '初始学习率',
  optimizer: '优化器', weight_decay: '权重衰减', dropout: 'Dropout', amp: '混合精度',
  deterministic: '确定性模式', cache: '图像缓存', save_period: '检查点保存间隔（轮）',
  plots: '生成评估图', name: '训练名称', weights: '初始化权重', weights_sha256: '初始化权重 SHA256',
};
const MODULE_ROLES = {
  Conv: '卷积提取局部纹理与下采样', C3k2: '残差特征提取与融合',
  SPPF: '空间金字塔池化，聚合多尺度信息', C2PSA: '注意力增强特征',
  Classify: '全局汇聚并输出类别概率',
};
let current = null;
let lastUpdate = 0;
let renderError = null;
let toastTimer = null;
let disposed = false;
let unsubscribe = null;

function html(id, value) {
  if ($(id).innerHTML !== value) $(id).innerHTML = value;
}
function text(id, value) { $(id).textContent = value; }
function kv(items) {
  return items.map(([key, value]) => `<div><dt>${escape(key)}</dt><dd>${escape(value)}</dd></div>`).join('');
}
function showToast(message) {
  text('toast', message);
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 6000);
}
async function action(callback) {
  try {
    const result = await callback();
    if (result?.error) throw new Error(result.error);
    if (result?.path) showToast(`已保存：${result.path}`);
    return result;
  } catch (error) { showToast(error.message); return null; }
}

function chart(rows, series, asPercent = false) {
  if (!rows.length) return '<p class="muted">等待首轮验证完成，曲线将自动出现。</p>';
  const width = 780, height = 215, left = 52, right = 16, top = 14, bottom = 30;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const values = rows.flatMap(row => series.map(item => row[item.key])).filter(Number.isFinite);
  const maximum = asPercent ? 1 : Math.max(...values, 0.01) * 1.08;
  const lastEpoch = Math.max(2, rows.at(-1).epoch);
  const x = epoch => left + (epoch - 1) / (lastEpoch - 1) * plotWidth;
  const y = value => top + (1 - value / maximum) * plotHeight;
  let output = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${asPercent ? '验证准确率' : '训练与验证损失'}曲线">`;
  for (let tick = 0; tick <= 4; tick++) {
    const value = maximum * tick / 4;
    output += `<line class="grid" x1="${left}" x2="${width - right}" y1="${y(value)}" y2="${y(value)}"/><text x="${left - 9}" y="${y(value) + 4}" text-anchor="end">${asPercent ? `${Math.round(value * 100)}%` : value.toFixed(2)}</text>`;
  }
  const ticks = [...new Set([1, Math.round(lastEpoch / 3), Math.round(lastEpoch * 2 / 3), lastEpoch])].filter(value => value >= 1);
  for (const tick of ticks) output += `<text x="${x(tick)}" y="${height - 7}" text-anchor="middle">${tick}</text>`;
  for (const item of series) {
    const valid = rows.filter(row => Number.isFinite(row[item.key]));
    output += `<polyline class="series-${item.color}" points="${valid.map(row => `${x(row.epoch)},${y(row[item.key])}`).join(' ')}"/>`;
    for (const row of valid) {
      output += `<circle class="point-${item.color}" cx="${x(row.epoch)}" cy="${y(row[item.key])}" r="3"><title>第 ${row.epoch} 轮 · ${escape(item.label)}：${asPercent ? percent(row[item.key]) : decimal(row[item.key], 5)}</title></circle>`;
    }
  }
  return output + '</svg>';
}

function renderOverview(data) {
  const batch = data.activeBatch;
  text('batch', batch ? `第 ${batch.epoch} 轮 · 批次 ${number(batch.batch)} / ${number(batch.batches)}`
    : data.trainingFinished ? '训练阶段已结束' : '验证完成后更新本轮指标');
  text('epoch', String(data.completedEpochs));
  text('epoch-total', `/ ${data.totalEpochs} 轮已完成`);
  text('percent', data.trainingFinished ? '训练完成' : `${data.progress.toFixed(1)}%`);
  $('progress').value = data.trainingFinished ? 100 : data.progress;
  text('timing', `运行时长 ${duration(data.elapsedSeconds)}`);
  text('eta', data.stage === 'completed' ? '评估、导出与系统验证均已完成'
    : data.trainingFinished ? '训练完成，评估和接入状态见下方记录' : `预计剩余 ${duration(data.etaSeconds)}`);
  html('metrics', [
    ['验证 Top-1', percent(data.latest?.top1), `最近完成第 ${data.latest?.epoch ?? '—'} 轮`],
    ['训练损失', decimal(data.latest?.trainLoss), batch ? `当前批次均值 ${decimal(batch.loss)}` : '最近完整轮次'],
    ['验证损失', decimal(data.latest?.valLoss), '越低通常表示拟合更好'],
    ['最高验证 Top-1', percent(data.best?.top1), `出现在第 ${data.best?.epoch ?? '—'} 轮`],
  ].map(([label, value, note]) => `<div class="metric"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>`).join(''));
  html('loss-chart', chart(data.history, [{ key: 'trainLoss', color: 'train', label: '训练损失' }, { key: 'valLoss', color: 'val', label: '验证损失' }]));
  html('accuracy-chart', chart(data.history, [{ key: 'top1', color: 'train', label: 'Top-1' }, { key: 'top5', color: 'val', label: 'Top-5' }], true));
  const gpu = data.gpu;
  const host = data.host;
  const hostMetrics = host ? `<dl>${kv([
    ['CPU 利用率', Number.isFinite(host.cpuUtilization) ? `${decimal(host.cpuUtilization, 0)}%` : '采样中'],
    ['系统内存占用', percent(host.memoryUsedRatio)],
    ['可用内存', `${decimal(host.availableMemory / 1024 ** 3, 2)} GB`],
  ])}</dl>${host.memoryPressure ? '<p class="caption">内存压力较高，分页读盘可能让 GPU 等待数据。当前不宜直接增大批量或开启内存缓存。</p>' : ''}` : '';
  html('hardware', (gpu?.available ? `<p class="hardware-name">${escape(gpu.name)}</p>
    <div class="gpu-metrics"><div><span>GPU 利用率</span><strong>${gpu.utilization ?? '—'}%</strong></div><div><span>温度</span><strong>${gpu.temperature ?? '—'} °C</strong></div></div>
    <progress class="memory-bar" max="${gpu.memoryTotalMb || 1}" value="${gpu.memoryUsedMb || 0}" aria-label="GPU 显存占用"></progress>
    <p class="caption">显存 ${number(gpu.memoryUsedMb)} / ${number(gpu.memoryTotalMb)} MB<br>设备整体占用，包含其他程序 · ${clock(gpu.sampledAt)}</p>`
    : `<p class="muted">${escape(gpu?.reason || '正在读取设备信息')}</p>`) + hostMetrics);
  const config = data.config.training;
  html('quick-config', kv([
    ['登录账号', data.viewer?.username || '—'],
    ['任务类型', '单叶病害分类'], ['模型', 'YOLO26m 骨干 + 分类头'],
    ['输入尺寸', `${config.imgsz} × ${config.imgsz}`], ['批量大小', config.batch],
    ['优化器', config.optimizer], ['当前学习率', data.latest?.learningRate?.toExponential(3) ?? '—'],
    ['提前停止', `${config.patience} 轮无改善`], ['进程', `${data.pid} · ${data.running ? '运行中' : '已退出'}`],
  ]));
  const counts = data.dataset?.counts;
  if (counts) {
    const total = data.dataset.images;
    html('dataset-summary', `<p><strong>${number(total)}</strong> 张图片 · ${data.classes.length} 类</p>
      <svg class="dataset-bar" width="100%" viewBox="0 0 100 8" preserveAspectRatio="none" aria-label="训练、验证和测试图片占比">
      <rect class="train" fill="var(--blue)" width="${counts.train / total * 100}" height="8"/>
      <rect fill="var(--cyan)" x="${counts.train / total * 100}" width="${counts.val / total * 100}" height="8"/>
      <rect fill="var(--warn)" x="${(counts.train + counts.val) / total * 100}" width="${counts.test / total * 100}" height="8"/></svg>
      <dl>${kv([['训练', number(counts.train)], ['验证', number(counts.val)], ['独立测试', number(counts.test)]])}</dl>`);
  }
  html('history-table', `<table><thead><tr><th>轮次</th><th>训练损失</th><th>验证损失</th><th>Top-1</th><th>Top-5</th><th>学习率</th><th>累计时间</th></tr></thead><tbody>${data.history.map(row => `<tr><td>${row.epoch}</td><td>${decimal(row.trainLoss)}</td><td>${decimal(row.valLoss)}</td><td>${percent(row.top1)}</td><td>${percent(row.top5)}</td><td>${row.learningRate?.toExponential(3) ?? '—'}</td><td>${duration(row.seconds)}</td></tr>`).join('')}</tbody></table>`);
}

function renderNetwork(data) {
  const network = data.network;
  const transfer = data.transfer;
  html('network-summary', [
    ['1', '分类模型'], [number(transfer?.total_parameters), '参数总量'],
    [network?.module_count ?? '—', '模块总数（含容器）'], [network?.leaf_module_count ?? '—', '底层计算模块'],
    [number(transfer?.verified_backbone_tensors), '逐项核验的迁移张量'],
  ].map(([value, label]) => `<div><strong>${value}</strong><span>${label}</span></div>`).join(''));
  html('network-flow', [
    ['输入图像', `RGB · 3 × ${data.config.training.imgsz} × ${data.config.training.imgsz}`],
    ['骨干网络', `${transfer?.backbone_layers ?? '—'} 个顶层模块 · 迁移初始化权重`],
    ['分类头', '全局池化 + 全连接 + Softmax'],
    ['分类输出', `${data.classes.length} 类概率`],
  ].map(([title, note]) => `<div class="network-block"><strong>${title}</strong><small>${note}</small></div>`).join('<span class="flow-arrow" aria-hidden="true">→</span>'));
  html('network-table', network ? `<table><thead><tr><th>模块</th><th>类型</th><th class="number">参数量</th><th>输出形状</th><th>作用</th></tr></thead><tbody>${network.layers.map(layer => `<tr><td>${layer.index} · ${layer.section === 'head' ? '分类头' : '骨干'}</td><td>${escape(layer.type)}</td><td class="number">${number(layer.parameters)}</td><td>${escape(JSON.stringify(layer.output_shape))}</td><td>${escape(MODULE_ROLES[layer.type] || '网络计算模块')}</td></tr>`).join('')}</tbody></table>` : '<p class="muted">尚未生成完整网络结构清单。迁移参数信息已在上方显示。</p>');
  html('all-config', kv(Object.entries(data.config.training).map(([key, value]) => [PARAMETERS[key] || key, typeof value === 'boolean' ? (value ? '启用' : '关闭') : value])));
  html('environment', kv([
    ['迁移参数元素数（含状态量）', number(transfer?.transferred_parameters)],
    ['原权重 SHA256', transfer?.source_sha256 || '—'],
    ['PyTorch', data.environment?.torch || '—'], ['Ultralytics', data.environment?.ultralytics || '—'],
    ['Python', data.environment?.python?.split('\n')[0] || '—'],
    ['数据清单 SHA256', data.dataset?.manifestSha256 || '—'],
  ]));
}

function renderClasses() {
  if (!current) return;
  const crops = [...new Set(current.classes.map(item => item.crop))].sort((a, b) => a.localeCompare(b, 'zh-CN'));
  const selected = $('crop-filter').value;
  const options = '<option value="">全部作物</option>' + crops.map(crop => `<option value="${escape(crop)}">${escape(crop)}</option>`).join('');
  if ($('crop-filter').innerHTML !== options) { $('crop-filter').innerHTML = options; $('crop-filter').value = selected; }
  const query = $('class-search').value.trim().toLowerCase();
  const rows = current.classes.filter(item => (!selected || item.crop === selected) && `${item.key} ${item.label} ${item.description}`.toLowerCase().includes(query));
  text('class-summary', `${crops.length} 种作物 · ${current.classes.length} 个分类`);
  const audit = current.dataset;
  text('leakage', audit && audit.crossSplitLeafOverlap === 0 && audit.crossSplitHashOverlap === 0 ? '叶片与文件摘要跨集重叠：0' : '数据审计尚未完成');
  text('class-count', `显示 ${rows.length} / ${current.classes.length} 类`);
  html('class-table', `<table><thead><tr><th>ID</th><th>作物</th><th>类别与识别目标</th><th class="number">训练</th><th class="number">验证</th><th class="number">测试</th></tr></thead><tbody>${rows.map(item => `<tr><td>${item.index}</td><td>${escape(item.crop)}</td><td><strong class="${item.healthy ? 'healthy-label' : ''}">${escape(item.label)}</strong><small>${escape(item.description)}</small><small class="raw-label">${escape(item.key)}</small></td><td class="number">${number(item.counts.train)}</td><td class="number">${number(item.counts.val)}</td><td class="number">${number(item.counts.test)}</td></tr>`).join('') || '<tr><td colspan="6">没有符合筛选条件的类别。</td></tr>'}</tbody></table>`);
}

function renderEvaluation() {
  if (!current) return;
  html('evaluation-summary', [['完整验证集', current.validation], ['独立测试集', current.test]].map(([title, report]) => `<section class="evaluation-result"><h3>${title}</h3>${report
    ? `<div class="evaluation-values"><div><strong>${percent(report.top1)}</strong><span>Top-1 准确率</span></div><div><strong>${decimal(report.macro_f1)}</strong><span>宏平均 F1</span></div></div><p class="caption">${number(report.images)} 张图片 · 置信度门槛覆盖率 ${percent(report.coverage)}</p>`
    : '<p class="muted">等待训练完成后独立评估。此处不使用中间轮次指标。</p>'}</section>`).join(''));
  html('artifacts', current.artifacts.map(item => `<div class="artifact"><div><strong>${escape(item.label)}</strong><small>${escape(item.path)}</small></div><span class="artifact-format">${item.format}</span><span class="artifact-status">${item.exists ? `${decimal(item.bytes / 1024 / 1024, 2)} MB · ${clock(item.modifiedAt)}` : '尚未生成'}</span><button data-artifact="${item.id}" ${item.exists ? '' : 'disabled'}>定位文件</button></div>`).join(''));
  const manifest = current.manifest;
  html('export-parameters', manifest ? `<dl class="config-grid">${kv([
    ['模型状态', manifest.validation_passed ? '验证门槛通过' : '验证门槛未通过'],
    ['任务', manifest.task], ['输入尺寸', `${manifest.image_size} × ${manifest.image_size}`],
    ['分类数量', manifest.classes.length], ['复核置信度阈值', manifest.threshold],
    ['预处理', manifest.preprocessing], ['PyTorch / ONNX 最大误差', manifest.onnx_max_abs_error],
    ['ONNX SHA256', manifest.onnx_sha256], ['最终权重 SHA256', manifest.weights_sha256],
    ['系统接口验证', current.verification?.passed ? '已通过真实模型接口检查' : '尚未完成'],
    ['发布目录', current.deployment?.release || '尚未启用发布版本'],
  ])}</dl><p class="caption">配置发布版本不等于系统验收完成，最终以系统实测报告为准。</p>` : '<p class="muted">最终导出参数将在训练、完整评估和 ONNX 一致性校验完成后自动同步。</p>');
  const report = current[$('evaluation-split').value];
  html('evaluation-table', report ? `<table><thead><tr><th>类别</th><th class="number">Precision</th><th class="number">Recall</th><th class="number">F1</th><th class="number">样本数</th></tr></thead><tbody>${current.classes.map(item => {
    const row = report.per_class[item.key];
    return row ? `<tr><td>${escape(item.label)}<small>${escape(item.key)}</small></td><td class="number">${decimal(row.precision)}</td><td class="number">${decimal(row.recall)}</td><td class="number">${decimal(row['f1-score'])}</td><td class="number">${number(row.support)}</td></tr>` : '';
  }).join('')}</tbody></table>` : '<p class="muted">该评估报告尚未生成。</p>');
}

function render(payload) {
  if (disposed) return;
  renderError = payload.error;
  $('error').hidden = !renderError && !payload.snapshot?.error;
  text('error', renderError || payload.snapshot?.error || '');
  if (!payload.snapshot) {
    current = null;
    lastUpdate = 0;
    $('workspace').hidden = true;
    $('empty').hidden = true;
    updateConnection();
    return;
  }
  current = payload.snapshot;
  text('node-context', current.context?.nodeName || 'YOLO 训练节点');
  if (!payload.error) lastUpdate = Date.now();
  $('empty').hidden = true;
  $('workspace').hidden = false;
  text('run-name', current.name);
  text('project-path', current.projectRoot);
  const evaluation = current.stage.startsWith('evaluating') && current.evaluation.total
    ? ` · ${number(current.evaluation.evaluated)} / ${number(current.evaluation.total)}` : '';
  text('stage', (STAGES[current.stage] || current.stage) + evaluation);
  $('stage').className = `state ${['failed', 'quality_gate_failed', 'interrupted'].includes(current.stage) ? 'failed' : current.trainingFinished ? 'finished' : ''}`;
  text('updated', `最近轮次同步 ${clock(current.epochUpdatedAt)}`);
  text('footer-status', `数据读取 ${clock(current.observedAt)} · 当前任务 ${current.pid}`);
  renderOverview(current);
  renderNetwork(current);
  renderClasses();
  renderEvaluation();
  const logText = current.logs.join('\n') || '等待训练输出…';
  if ($('log-output').textContent !== logText) {
    text('log-output', logText);
    if ($('follow-log').checked) $('log-output').scrollTop = $('log-output').scrollHeight;
  }
  text('error-output', current.errors.join('\n') || '暂无错误输出。');
  updateConnection();
}

function updateConnection() {
  const disconnected = Boolean(renderError) || (lastUpdate > 0 && Date.now() - lastUpdate > 10000);
  $('connection').classList.toggle('disconnected', disconnected);
  text('connection', disconnected ? '同步中断 · 保留上次数据' : lastUpdate ? '实时同步 · 2 秒' : '等待训练数据');
}

root.querySelectorAll('[data-tab]').forEach(button => {
  button.addEventListener('click', () => {
    for (const tab of root.querySelectorAll('[data-tab]')) {
      const selected = tab === button;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      $(tab.dataset.tab).hidden = !selected;
    }
  });
  button.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const tabs = [...root.querySelectorAll('[data-tab]')];
    const index = tabs.indexOf(button);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
      : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    tabs[next].click(); tabs[next].focus();
  });
});
$('refresh').onclick = () => action(() => api.refresh());
$('crop-filter').onchange = renderClasses;
$('class-search').oninput = renderClasses;
$('evaluation-split').onchange = renderEvaluation;
$('artifacts').onclick = event => {
  const button = event.target.closest('[data-artifact]');
  if (button) action(() => api.reveal(button.dataset.artifact));
};
$('export-csv').onclick = () => action(() => api.exportSnapshot('csv'));
$('export-json').onclick = () => action(() => api.exportSnapshot('json'));
if (!api) {
  $('error').hidden = false;
  text('error', '本地训练数据需要在 Flowly 桌面端中查看。');
} else {
  unsubscribe = api.onUpdate(render);
  api.start().then(payload => render(payload))
    .catch(error => { if (!disposed) render({ snapshot: null, error: error.message }); });
}
const connectionTimer = setInterval(updateConnection, 2000);
return () => {
  disposed = true;
  unsubscribe?.();
  clearInterval(connectionTimer);
  clearTimeout(toastTimer);
  api?.stop().catch(() => {});
};
}
