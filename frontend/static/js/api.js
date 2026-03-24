(function () {
  const baseRaw = window.API_BASE_URL || "";
  const base = baseRaw.replace(/\/$/, "");
  window.apiUrl = function (path) {
    if (!path) return base || "";
    if (!base) return path;
    if (path.startsWith("http://") || path.startsWith("https://")) return path;
    return base + (path.startsWith("/") ? path : "/" + path);
  };
})();
