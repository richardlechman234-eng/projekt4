document.querySelectorAll("[data-co]").forEach(function (el) {
  var v = (window.PLS || {})[el.dataset.co];
  if (v) el.textContent = v; else { el.textContent = "doplniť"; el.classList.add("todo"); }
});
var y = document.getElementById("y"); if (y) y.textContent = new Date().getFullYear();

var rb = document.getElementById("consent-reset");
if (rb) rb.addEventListener("click", function () {
  try { localStorage.removeItem("pls-map"); localStorage.removeItem("pls-google"); localStorage.removeItem("pls-consent"); } catch (e) {}
  document.getElementById("consent-msg").textContent = "Súhlas je zrušený.";
});
