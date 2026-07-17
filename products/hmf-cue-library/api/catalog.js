// api/catalog.js
//
// Public storefront listing endpoint. Serves METADATA + PREVIEWS ONLY.
// No entitlement required; no file paths or audio bytes are ever exposed here.
// The store UI (public/store.html) fetches this to render the catalog.

'use strict';

const { loadCatalog, publicView } = require('../engine/catalog');

module.exports = async function handler(req, res) {
  try {
    const cat = loadCatalog();
    const view = publicView(cat);
    res.setHeader('Content-Type', 'application/json');
    return res.status(200).json(view);
  } catch (err) {
    console.error('[api/catalog] error:', err && err.message);
    return res.status(500).json({ error: 'catalog_error', message: 'Could not load the catalog.' });
  }
};
