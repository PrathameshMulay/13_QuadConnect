/*
 * Draws every Vega-Lite chart on the page.
 *
 * An element with data-vega-spec="<url>" gets the spec at that URL, drawn
 * by vega-embed as SVG (crisp at any size, and readable by screen readers
 * through the spec's description and each mark's values).
 *
 * vega-embed's "..." menu and hover tooltips are switched off: the menu's
 * image downloads work only with a mouse, and the tooltips cannot be
 * dismissed or hovered (WCAG 2.1.1, 1.4.13). The PNG/JPG link and the table
 * under each chart give the same things to everyone.
 *
 * Without JavaScript the page shows the server-rendered image in the
 * <noscript> next to each chart, so nothing here is required to read it.
 */
document.querySelectorAll("[data-vega-spec]").forEach(function (container) {
  vegaEmbed(container, container.dataset.vegaSpec, {
    renderer: "svg",
    actions: false,
    tooltip: false,
  }).catch(function (error) {
    var note = document.createElement("p");
    note.setAttribute("role", "alert");
    note.textContent = "This chart could not be drawn. Its numbers are in the table below.";
    container.replaceChildren(note);
    console.error(error);
  });
});
