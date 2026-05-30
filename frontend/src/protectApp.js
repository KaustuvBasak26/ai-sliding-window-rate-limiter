/** Production-only deterrents; bypassable by determined users. */
export function enableProductionProtections() {
  if (!import.meta.env.PROD) {
    return;
  }

  document.addEventListener("contextmenu", (event) => {
    event.preventDefault();
  });

  document.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    const blocked =
      key === "f12" ||
      (event.ctrlKey && event.shiftKey && ["i", "j", "c", "k"].includes(key)) ||
      (event.metaKey && event.altKey && ["i", "j", "c"].includes(key)) ||
      (event.ctrlKey && key === "u") ||
      (event.metaKey && key === "u");

    if (blocked) {
      event.preventDefault();
    }
  });

  document.addEventListener("selectstart", (event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
      return;
    }
    event.preventDefault();
  });

  document.addEventListener("dragstart", (event) => {
    event.preventDefault();
  });
}
