/**
 * request 工具函数单元测试
 * 测试字段转换函数（纯函数，无需 mock）
 */

const mockRequest = {
  get: jest.fn().mockResolvedValue({}),
  post: jest.fn().mockResolvedValue({}),
  put: jest.fn().mockResolvedValue({}),
  patch: jest.fn().mockResolvedValue({}),
  delete: jest.fn().mockResolvedValue({}),
  stream: jest.fn().mockResolvedValue({})
}

jest.mock('js-cookie', () => ({ get: jest.fn(), set: jest.fn(), remove: jest.fn() }))
jest.mock('element-plus', () => ({ ElMessage: { error: jest.fn(), success: jest.fn(), warning: jest.fn() } }))
jest.mock('@/router', () => ({ push: jest.fn() }))
jest.mock('@/config', () => ({
  APP_CONFIG: { apiBaseUrl: 'http://localhost:8000', apiPrefix: '/api/v1' },
  getApiBaseUrl: () => 'http://localhost:8000/api/v1'
}))

let toCamelCase, toSnakeCase, toCamelCaseKeys, toSnakeCaseKeys

beforeAll(async () => {
  jest.mock('axios', () => {
    const mockInstance = {
      get: jest.fn().mockResolvedValue({ data: {} }),
      post: jest.fn().mockResolvedValue({ data: {} }),
      interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } },
      defaults: { baseURL: 'http://localhost:8000/api/v1' }
    }
    return {
      __esModule: true,
      default: mockInstance,
      create: jest.fn(() => mockInstance)
    }
  })

  const mod = require('@/api/index')
  toCamelCase = mod.toCamelCase
  toSnakeCase = mod.toSnakeCase
  toCamelCaseKeys = mod.toCamelCaseKeys
  toSnakeCaseKeys = mod.toSnakeCaseKeys
})

// ============================================================
// toCamelCase
// ============================================================

describe('toCamelCase', () => {
  it('snake_case → camelCase', () => {
    expect(toCamelCase('user_name')).toBe('userName')
  })

  it('多段下划线', () => {
    expect(toCamelCase('created_at_time')).toBe('createdAtTime')
  })

  it('已是 camelCase 不变', () => {
    expect(toCamelCase('userName')).toBe('userName')
  })

  it('全小写无下划线不变', () => {
    expect(toCamelCase('username')).toBe('username')
  })
})

// ============================================================
// toSnakeCase
// ============================================================

describe('toSnakeCase', () => {
  it('camelCase → snake_case', () => {
    expect(toSnakeCase('userName')).toBe('user_name')
  })

  it('多个大写字母', () => {
    expect(toSnakeCase('createdAtTime')).toBe('created_at_time')
  })

  it('已是 snake_case 不变', () => {
    expect(toSnakeCase('user_name')).toBe('user_name')
  })

  it('全小写不变', () => {
    expect(toSnakeCase('username')).toBe('username')
  })
})

// ============================================================
// toCamelCaseKeys
// ============================================================

describe('toCamelCaseKeys', () => {
  it('平铺对象键转换', () => {
    const input = { user_id: 1, created_at: '2026-01-01' }
    const result = toCamelCaseKeys(input)
    expect(result).toEqual({ userId: 1, createdAt: '2026-01-01' })
  })

  it('嵌套对象递归转换', () => {
    const input = { user_info: { first_name: 'Alice' } }
    const result = toCamelCaseKeys(input)
    expect(result).toEqual({ userInfo: { firstName: 'Alice' } })
  })

  it('数组中的对象也转换', () => {
    const input = [{ user_id: 1 }, { user_id: 2 }]
    const result = toCamelCaseKeys(input)
    expect(result).toEqual([{ userId: 1 }, { userId: 2 }])
  })

  it('null 返回 null', () => {
    expect(toCamelCaseKeys(null)).toBeNull()
  })

  it('undefined 返回 undefined', () => {
    expect(toCamelCaseKeys(undefined)).toBeUndefined()
  })

  it('基础类型原样返回', () => {
    expect(toCamelCaseKeys('hello')).toBe('hello')
    expect(toCamelCaseKeys(42)).toBe(42)
  })
})

// ============================================================
// toSnakeCaseKeys
// ============================================================

describe('toSnakeCaseKeys', () => {
  it('平铺对象键转换', () => {
    const input = { userId: 1, createdAt: '2026-01-01' }
    const result = toSnakeCaseKeys(input)
    expect(result).toEqual({ user_id: 1, created_at: '2026-01-01' })
  })

  it('嵌套对象递归转换', () => {
    const input = { userInfo: { firstName: 'Alice' } }
    const result = toSnakeCaseKeys(input)
    expect(result).toEqual({ user_info: { first_name: 'Alice' } })
  })

  it('数组中的对象也转换', () => {
    const input = [{ userId: 1 }, { userId: 2 }]
    const result = toSnakeCaseKeys(input)
    expect(result).toEqual([{ user_id: 1 }, { user_id: 2 }])
  })

  it('null 返回 null', () => {
    expect(toSnakeCaseKeys(null)).toBeNull()
  })
})
