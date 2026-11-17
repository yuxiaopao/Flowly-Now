module.exports = {
  plugins: [
    function viteTestEnvironment({ types }) {
      return {
        visitor: {
          MetaProperty(path) {
            if (path.node.meta.name !== 'import' || path.node.property.name !== 'meta') return
            const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => key.startsWith('VITE_')))
            Object.assign(env, {
              MODE: 'test',
              DEV: process.env.NODE_ENV !== 'production',
              PROD: process.env.NODE_ENV === 'production',
              BASE_URL: '/'
            })
            path.replaceWith(types.objectExpression([
              types.objectProperty(types.identifier('env'), types.valueToNode(env))
            ]))
          }
        }
      }
    }
  ],
  presets: [
    ['@babel/preset-env', {
      targets: { node: 'current' }
    }]
  ]
}
