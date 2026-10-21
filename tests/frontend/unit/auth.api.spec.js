/**
 * 认证 API 单元测试
 * 测试 authApi 的所有方法调用正确的 URL 和参数
 */

const mockRequest = {
  get: jest.fn().mockResolvedValue({}),
  post: jest.fn().mockResolvedValue({}),
  put: jest.fn().mockResolvedValue({}),
  patch: jest.fn().mockResolvedValue({}),
  delete: jest.fn().mockResolvedValue({}),
  stream: jest.fn().mockResolvedValue({})
}

jest.mock('@/api/index', () => ({
  request: mockRequest,
  api: {},
  default: {},
  toCamelCase: (str) => str.replace(/_([a-z])/g, (_, l) => l.toUpperCase()),
  toSnakeCase: (str) => str.replace(/[A-Z]/g, (l) => `_${l.toLowerCase()}`),
  toCamelCaseKeys: (obj) => obj,
  toSnakeCaseKeys: (obj) => obj
}))

const { authApi } = require('@/api/auth')

beforeEach(() => {
  jest.clearAllMocks()
})

describe('authApi.login', () => {
  it('POST /auth/login/ 携带用户名和密码', async () => {
    await authApi.login({ username: 'testuser', password: 'pass123' })
    expect(mockRequest.post).toHaveBeenCalledWith('/auth/login/', { username: 'testuser', password: 'pass123' }, { skipErrorToast: true })
  })

  it('登录失败时 reject', async () => {
    mockRequest.post.mockRejectedValueOnce(new Error('401'))
    await expect(authApi.login({ username: 'bad', password: 'bad' })).rejects.toThrow()
  })
})

describe('authApi.register', () => {
  it('POST /auth/register/ 携带注册数据', async () => {
    const payload = { username: 'newuser', password: 'pass123', email: 'new@example.com' }
    await authApi.register(payload)
    expect(mockRequest.post).toHaveBeenCalledWith('/auth/register/', payload, { skipErrorToast: true })
  })
})

describe('authApi.logout', () => {
  it('POST /auth/logout/', async () => {
    await authApi.logout()
    expect(mockRequest.post).toHaveBeenCalledWith('/auth/logout/')
  })
})

describe('authApi.getUserInfo', () => {
  it('GET /auth/user/', async () => {
    mockRequest.get.mockResolvedValueOnce({ id: 1, username: 'testuser', role: 'developer' })
    const result = await authApi.getUserInfo()
    expect(mockRequest.get).toHaveBeenCalledWith('/auth/user/', {}, { skipAuthRedirect: true })
    expect(result).toMatchObject({ id: 1 })
  })
})

describe('authApi.updateProfile', () => {
  it('PATCH /auth/user/ 更新用户资料', async () => {
    await authApi.updateProfile({ bio: '新简介' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/auth/user/', { bio: '新简介' }, { skipErrorToast: true })
  })
})

describe('authApi.changePassword', () => {
  it('POST /auth/change-password/ 携带旧密码和新密码', async () => {
    await authApi.changePassword({ old_password: 'old123', new_password: 'new456' })
    expect(mockRequest.post).toHaveBeenCalledWith('/auth/change-password/', { old_password: 'old123', new_password: 'new456' }, { skipErrorToast: true })
  })
})

describe('authApi.refreshToken', () => {
  it('POST /auth/refresh/ 携带 refresh token', async () => {
    await authApi.refreshToken('my_refresh_token')
    expect(mockRequest.post).toHaveBeenCalledWith('/auth/refresh/', { refresh: 'my_refresh_token' })
  })
})

describe('authApi.requestPasswordReset', () => {
  it('POST /auth/password-reset/ 携带邮箱', async () => {
    await authApi.requestPasswordReset('user@example.com')
    expect(mockRequest.post).toHaveBeenCalledWith('/auth/password-reset/', { email: 'user@example.com' }, { skipErrorToast: true })
  })
})

describe('authApi.resetPassword', () => {
  it('POST /auth/password-reset/confirm/ 携带 uid、token 和新密码', async () => {
    await authApi.resetPassword('UID123', 'TOKEN456', 'newpass789')
    expect(mockRequest.post).toHaveBeenCalledWith('/auth/password-reset/confirm/', {
      uidb64: 'UID123',
      token: 'TOKEN456',
      new_password: 'newpass789'
    }, { skipErrorToast: true })
  })
})
