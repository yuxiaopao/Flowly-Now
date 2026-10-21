/**
 * System API methods
 */

import { request } from './index'

export const systemApi = {
  healthCheck() {
    return request.get('/health/')
  },

  ping() {
    return request.get('/ping/')
  },

  /** Server-side hardware detection only */
  getCapabilitiesServer() {
    return request.get('/system/capabilities/')
  },

  /** Merge browser + server hardware profile for NL / YOLO tuning */
  getCapabilities(clientCapabilities) {
    if (clientCapabilities) {
      return request.post('/system/capabilities/', { client_capabilities: clientCapabilities })
    }
    return request.get('/system/capabilities/')
  },
}

export default systemApi
