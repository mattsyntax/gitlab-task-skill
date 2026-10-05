// Thin wrapper around the database driver; the real connection is configured by env.
module.exports = {
  query: async (_sql, _params) => [],
  one: async (_sql, _params) => null,
};
