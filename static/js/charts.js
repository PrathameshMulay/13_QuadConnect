/*
 * Draws every Vega-Lite chart on the page.
 *
 * An element with data-vega-spec="<url>" gets the spec at that URL, drawn
 * by vega-embed as SVG (crisp at any size, and readable by screen readers
 * through the spec's description). The "..." menu offers the image
 * downloads, the spec, and "Open in Vega Editor".
 *
 * Without JavaScript the page shows the server-rendered image in the
 * <noscript> next to each chart, so nothing here is required to read it.
 */
document.querySelectorAll("[data-vega-spec]").forEach(function (container) {
  var url = container.dataset.vegaSpec;
  vegaEmbed(container, url, {
    renderer: "svg",
    actions: { export: true, source: true, compiled: false, editor: true },
    downloadFileName: url.split("/").pop().replace(".vl.json", ""),
  }).then(function () {
    // The menu button is an icon only; give it a name screen readers can say.
    var menu = container.querySelector("summary");
    if (menu) menu.setAttribute("aria-label", "Chart menu");
  }).catch(function (error) {
    container.textContent =
      "This chart could not be drawn. Its numbers are in the table below.";
    console.error(error);
  });
});
