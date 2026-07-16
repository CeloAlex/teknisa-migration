// Interações que não valem a pena puxar htmx/Alpine para resolver.

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".dropzone[data-input]").forEach((zona) => {
    const input = document.getElementById(zona.dataset.input);
    if (!input) return;
    zona.addEventListener("click", () => input.click());
    zona.addEventListener("dragover", (e) => {
      e.preventDefault();
      zona.classList.add("over");
    });
    zona.addEventListener("dragleave", () => zona.classList.remove("over"));
    zona.addEventListener("drop", (e) => {
      e.preventDefault();
      zona.classList.remove("over");
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        const rotulo = zona.querySelector("[data-rotulo]");
        if (rotulo) rotulo.textContent = input.files[0].name;
      }
    });
    input.addEventListener("change", () => {
      const rotulo = zona.querySelector("[data-rotulo]");
      if (rotulo && input.files.length) rotulo.textContent = input.files[0].name;
    });
  });

  // Toggle do select de organização no form de operador — só administrador/auditor
  // enxergam todas as organizações (nr_org nulo); os demais papéis exigem uma organização.
  const papelSelect = document.getElementById("papel");
  const orgField = document.getElementById("campo-organizacao");
  if (papelSelect && orgField) {
    const atualizar = () => {
      const precisaOrg = !["administrador", "auditor"].includes(papelSelect.value);
      orgField.style.display = precisaOrg ? "" : "none";
      orgField.querySelector("select").required = precisaOrg;
    };
    papelSelect.addEventListener("change", atualizar);
    atualizar();
  }
});
