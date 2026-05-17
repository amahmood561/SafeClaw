const copyButtons = document.querySelectorAll("[data-copy]");

copyButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.querySelector(button.getAttribute("data-copy"));
    if (!target) return;
    const text = target.innerText.trim();
    try {
      await navigator.clipboard.writeText(text);
      const original = button.innerText;
      button.innerText = "Copied";
      setTimeout(() => {
        button.innerText = original;
      }, 1400);
    } catch {
      button.innerText = "Copy failed";
    }
  });
});
