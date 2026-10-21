export const AUTH = {
  accessKey: 'access_token',
  refreshKey: 'refresh_token',
  rememberKey: 'auth_remember',
  logoutKey: 'auth_logout',
  cookieDays: { access: 1, refresh: 7 },
  passwordMinLength: 8,
  usernameMaxLength: 150,
  safeRetryDelay: 800,
  configNotice: {
    title: '注册配置暂时不可用',
    message: '暂时无法获取注册配置，请稍后重试。已有账号可以关闭提示后继续登录。',
    retry: '重新加载',
    dismiss: '关闭提示',
    width: 'min(440px, calc(100vw - 32px))',
  },
  routes: { login: '/login', home: '/home', forgot: '/forgot-password', reset: '/reset-password' },
  endpoints: {
    login: '/auth/login/', register: '/auth/register/', refresh: '/auth/refresh/',
    reset: '/auth/password-reset/', confirm: '/auth/password-reset/confirm/',
  },
}
