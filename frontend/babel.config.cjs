module.exports = {
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' } }],
    '@babel/preset-react',
  ],
  plugins: [
    function inlineImportMetaEnv() {
      return {
        visitor: {
          MetaProperty(path) {
            if (
              path.node.meta.name === 'import' &&
              path.node.property.name === 'meta'
            ) {
              path.replaceWithSourceString(
                '({ env: { VITE_API_URL: "http://localhost:8000", PROD: false, DEV: true, MODE: "test" } })'
              );
            }
          },
        },
      };
    },
  ],
};
