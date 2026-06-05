/**
 * Tenant API 单元测试
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
  toCamelCase: (str) => str,
  toSnakeCase: (str) => str,
  toCamelCaseKeys: (obj) => obj,
  toSnakeCaseKeys: (obj) => obj
}))

const tenantApi = require('@/api/tenant').default

beforeEach(() => jest.clearAllMocks())

describe('tenantApi.getTenants', () => {
  it('GET /tenants/tenants/', async () => {
    await tenantApi.getTenants()
    expect(mockRequest.get).toHaveBeenCalledWith('/tenants/tenants/', {})
  })
})

describe('tenantApi.getTenant', () => {
  it('GET /tenants/tenants/:id/', async () => {
    await tenantApi.getTenant(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/tenants/tenants/1/')
  })
})

describe('tenantApi.createTenant', () => {
  it('POST /tenants/tenants/', async () => {
    const data = { name: '新组织', slug: 'new-org' }
    await tenantApi.createTenant(data)
    expect(mockRequest.post).toHaveBeenCalledWith('/tenants/tenants/', data)
  })
})

describe('tenantApi.updateTenant', () => {
  it('PATCH /tenants/tenants/:id/', async () => {
    await tenantApi.updateTenant(1, { name: '更新' })
    expect(mockRequest.patch).toHaveBeenCalledWith('/tenants/tenants/1/', { name: '更新' })
  })
})

describe('tenantApi.deleteTenant', () => {
  it('DELETE /tenants/tenants/:id/', async () => {
    await tenantApi.deleteTenant(1)
    expect(mockRequest.delete).toHaveBeenCalledWith('/tenants/tenants/1/')
  })
})

describe('tenantApi.getTenantUsage', () => {
  it('GET /tenants/tenants/:id/usage/', async () => {
    await tenantApi.getTenantUsage(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/tenants/tenants/1/usage/')
  })
})

describe('tenantApi.getTenantMembers', () => {
  it('GET /tenants/tenants/:id/members/', async () => {
    await tenantApi.getTenantMembers(1)
    expect(mockRequest.get).toHaveBeenCalledWith('/tenants/tenants/1/members/')
  })
})

describe('tenantApi.inviteMember', () => {
  it('POST /tenants/tenants/:id/invite/', async () => {
    const data = { email: 'new@example.com', role: 'developer' }
    await tenantApi.inviteMember(1, data)
    expect(mockRequest.post).toHaveBeenCalledWith('/tenants/tenants/1/invite/', data)
  })
})

describe('tenantApi.removeMember', () => {
  it('DELETE /tenants/tenants/:id/remove_member/', async () => {
    await tenantApi.removeMember(1, 42)
    expect(mockRequest.delete).toHaveBeenCalledWith('/tenants/tenants/1/remove_member/', { member_id: 42 })
  })
})

describe('tenantApi.getMyMemberships', () => {
  it('GET /tenants/memberships/my_memberships/', async () => {
    await tenantApi.getMyMemberships()
    expect(mockRequest.get).toHaveBeenCalledWith('/tenants/memberships/my_memberships/')
  })
})

describe('tenantApi.getInvitations', () => {
  it('GET /tenants/invitations/', async () => {
    await tenantApi.getInvitations()
    expect(mockRequest.get).toHaveBeenCalledWith('/tenants/invitations/', {})
  })
})

describe('tenantApi.getPendingInvitations', () => {
  it('GET /tenants/invitations/pending/', async () => {
    await tenantApi.getPendingInvitations()
    expect(mockRequest.get).toHaveBeenCalledWith('/tenants/invitations/pending/')
  })
})

describe('tenantApi.joinTenant', () => {
  it('POST /tenants/invitations/join/', async () => {
    await tenantApi.joinTenant({ invite_code: 'ABC123' })
    expect(mockRequest.post).toHaveBeenCalledWith('/tenants/invitations/join/', { invite_code: 'ABC123' })
  })
})

describe('tenantApi.acceptInvitation', () => {
  it('POST /tenants/invitations/:id/accept/', async () => {
    await tenantApi.acceptInvitation(5)
    expect(mockRequest.post).toHaveBeenCalledWith('/tenants/invitations/5/accept/')
  })
})

describe('tenantApi.declineInvitation', () => {
  it('POST /tenants/invitations/:id/decline/', async () => {
    await tenantApi.declineInvitation(5)
    expect(mockRequest.post).toHaveBeenCalledWith('/tenants/invitations/5/decline/')
  })
})

describe('tenantApi.refreshUsage', () => {
  it('POST /tenants/usage/refresh/', async () => {
    await tenantApi.refreshUsage(1)
    expect(mockRequest.post).toHaveBeenCalledWith('/tenants/usage/refresh/', { tenant_id: 1 })
  })
})
