import { INTEGRATION_STATES, INTEGRATION_UI, INTEGRATION_DATE_LOCALE } from '@/config/integrationCatalog'

export const camelField = key => key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())

export function connectionState(connection) {
  if (!connection) return 'unconfigured'
  if (connection.isActive === false || connection.verificationStatus === 'disconnected') return 'disconnected'
  if (connection.verificationStatus === 'failed') return 'failed'
  if (connection.isConnected && connection.verificationStatus === 'success' && connection.lastCheckedAt) return 'success'
  return 'untested'
}

export function serviceConnections(service, connections) {
  return connections.filter(item => item.integrationType === service.id)
}

export function primaryConnection(service, connections) {
  const matches = serviceConnections(service, connections)
  return matches.find(item => connectionState(item) === 'success') || matches[0]
}

export function filterCatalog(catalog, connections, { category = 'all', status = 'all', query = '' } = {}) {
  const term = query.trim().toLocaleLowerCase()
  return catalog.filter(service => {
    const matches = serviceConnections(service, connections)
    const states = matches.length ? matches.map(connectionState) : ['unconfigured']
    return (category === 'all' || service.category === category)
      && (status === 'all' || states.includes(status))
      && (!term || [service.name, service.id, service.description, ...(service.capabilities || [])].join(' ').toLocaleLowerCase().includes(term))
  })
}

export function connectionForm(service, connection) {
  const fields = Object.fromEntries(service.fields.map(field => [field.key,
    field.secret ? '' : (connection?.config?.[camelField(field.key)] ?? connection?.config?.[field.key] ?? '')]))
  return { name: connection?.name || service.name, fields, events: [...(connection?.config?.events || [])], clearSecrets: [] }
}

export function connectionPayload(service, form, connection) {
  const config = { events: [...form.events] }, credentials = {}
  for (const field of service.fields) {
    const value = (form.fields[field.key] || '').trim()
    if (!field.secret) config[field.key] = value
    else if (form.clearSecrets.includes(field.key)) credentials[field.key] = ''
    else if (value || !connection?.configuredFields?.includes(field.key)) credentials[field.key] = value
  }
  return { name: form.name.trim(), integrationType: service.id, config, credentials }
}

export function validateConnectionForm(service, form, connection) {
  const errors = {}
  if (!form.name.trim()) errors.name = `${INTEGRATION_UI.required}${INTEGRATION_UI.name}`
  for (const field of service.fields) {
    const supplied = form.fields[field.key]?.trim()
    const preserved = field.secret && connection?.configuredFields?.includes(field.key) && !form.clearSecrets.includes(field.key)
    if (field.required && !supplied && !preserved) errors[field.key] = `${INTEGRATION_UI.required}${field.label}`
  }
  return errors
}

export function formatConnectionDate(value) {
  if (!value) return INTEGRATION_UI.never
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? INTEGRATION_UI.never : date.toLocaleString(INTEGRATION_DATE_LOCALE)
}

export function stateMeta(connection) {
  return INTEGRATION_STATES[connectionState(connection)]
}
