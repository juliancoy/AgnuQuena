(function () {
  const storageKey = "agnuquena-theme";
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const storedTheme = localStorage.getItem(storageKey);
  let theme = storedTheme === "dark" || storedTheme === "light"
    ? storedTheme
    : (media.matches ? "dark" : "light");

  function applyTheme(nextTheme, persist = false) {
    theme = nextTheme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;

    const isDark = theme === "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.textContent = isDark ? "Day mode" : "Night mode";
      button.setAttribute("aria-pressed", String(isDark));
      button.setAttribute("title", `Switch to ${isDark ? "day" : "night"} mode`);
    });

    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.content = isDark ? "#061411" : "#eef4f0";
    if (persist) localStorage.setItem(storageKey, theme);
    window.dispatchEvent(new CustomEvent("agnuquena-themechange", { detail: { theme } }));
  }

  applyTheme(theme);

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme(theme);
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        applyTheme(theme === "dark" ? "light" : "dark", true);
      });
    });
  });

  window.addEventListener("storage", (event) => {
    if (event.key === storageKey && (event.newValue === "dark" || event.newValue === "light")) {
      applyTheme(event.newValue);
    }
  });

  media.addEventListener("change", (event) => {
    if (!localStorage.getItem(storageKey)) applyTheme(event.matches ? "dark" : "light");
  });
})();
