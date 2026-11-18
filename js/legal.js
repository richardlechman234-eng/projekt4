document.querySelectorAll("[data-co]").forEach(function (el) {
  var v = (window.PLS || {})[el.dataset.co];
  if (v) el.textContent = v; else { el.textContent = "doplniť"; el.classList.add("todo"); }
});
var y = document.getElementById("y"); if (y) y.textContent = new Date().getFullYear();
