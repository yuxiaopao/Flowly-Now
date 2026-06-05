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
  }
}

export default systemApi
