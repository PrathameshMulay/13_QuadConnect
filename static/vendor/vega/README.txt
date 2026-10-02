Vega, Vega-Lite and vega-embed, served from our own static files rather
than a CDN (no third-party request when a page loads, as with the font).

  vega.min.js         vega        6.4.0   cdn.jsdelivr.net/npm/vega@6.4.0/build/
  vega-lite.min.js    vega-lite   6.4.3   cdn.jsdelivr.net/npm/vega-lite@6.4.3/build/
  vega-embed.min.js   vega-embed  7.3.0   cdn.jsdelivr.net/npm/vega-embed@7.3.0/build/

Vega-Lite 6.4 is also the newest version vl-convert-python 1.9 renders,
so the charts on the page and the PNG/JPG endpoints use the same grammar.

One change from the published files: the trailing "//# sourceMappingURL"
comment is removed from vega-lite.min.js and vega-embed.min.js. The .map
files are not shipped, and Django's hashed static storage refuses to
collect a file that points at a missing source map.

Licence: BSD 3-Clause, University of Washington Interactive Data Lab
(LICENSE-*.txt).
