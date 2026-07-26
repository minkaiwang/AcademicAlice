/**
 * 当前发行没有打包上游 WebDAV 同步实现。
 *
 * 明确禁用相关控件，避免用户误以为“保存配置”或“立即同步”已经生效，
 * 也避免把第三方应用密码落入未经审计的浏览器存储。稳定 JSON 与自动备份
 * 仍由桌宠本机宿主提供。
 */

const CONTROL_IDS = [
  'syncAutoEnabled',
  'jianguoyunServerUrl',
  'jianguoyunUsername',
  'jianguoyunPassword',
  'btnJianguoyunTest',
  'btnJianguoyunSave',
  'btnJianguoyunDisconnect',
  'btnCloudSyncNow',
  'btnCloudUpload',
  'btnCloudDownload',
  'btnCloudKeepLocal',
  'btnCloudUseRemote',
  'btnCloudRetryMerge',
  'btnCloudShowLog',
];

function disableUnavailableCloudSync() {
  for (const id of CONTROL_IDS) {
    const element = document.getElementById(id);
    if (!element) continue;
    element.disabled = true;
    element.setAttribute('aria-disabled', 'true');
    element.title = '当前发行未启用云同步';
  }

  const status = document.getElementById('cloudSyncStatus');
  if (status) status.textContent = '当前发行未启用云同步';
  const hint = document.getElementById('syncPolicyHint');
  if (hint) {
    hint.textContent = '工作台仍会保存到本机稳定 JSON 并自动备份；WebDAV 功能待安全审计后再启用。';
  }
  const conflictActions = document.getElementById('cloudConflictActions');
  if (conflictActions) conflictActions.classList.add('hidden');
}

if (document.readyState === 'loading') {
  document.addEventListener(
    'DOMContentLoaded',
    disableUnavailableCloudSync,
    { once: true },
  );
} else {
  disableUnavailableCloudSync();
}
