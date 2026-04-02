document.addEventListener("DOMContentLoaded", () => {
  const fieldsEl = document.getElementById("fields");

  // Cargar imágenes si es DOCX
  if (document.getElementById("img-grid")) {
    fetch("/images")
      .then(r => r.json())
      .then(({ images }) => {
        const grid = document.getElementById("img-grid");
        images.forEach(b64 => {
          const img = document.createElement("img");
          img.src = `data:image/png;base64,${b64}`;
          grid.appendChild(img);
        });
      });
  }

  // Agregar fila al formulario
  function addRow(key = "", value = "") {
    const row = document.createElement("div");
    row.className = "field-row";
    row.innerHTML = `
      <input class="key" type="text" placeholder="campo" value="${escHtml(key)}">
      <input class="val" type="text" placeholder="valor" value="${escHtml(value)}">
      <button class="del" title="Eliminar">✕</button>
    `;
    row.querySelector(".del").addEventListener("click", () => row.remove());
    fieldsEl.appendChild(row);
    return row;
  }

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  // Poblar con los campos iniciales desde el servidor
  const initial = JSON.parse(document.getElementById("initial-data").textContent);
  Object.entries(initial).forEach(([k, v]) => addRow(k, v ?? ""));

  // Botón agregar campo vacío
  document.getElementById("btn-add").addEventListener("click", () => {
    const row = addRow();
    row.querySelector(".key").focus();
  });

  // Confirmar: recoger valores y enviar
  document.getElementById("btn-confirm").addEventListener("click", async () => {
    const fields = {};
    fieldsEl.querySelectorAll(".field-row").forEach(row => {
      const k = row.querySelector(".key").value.trim();
      const v = row.querySelector(".val").value.trim();
      if (k) fields[k] = v === "" ? null : v;
    });

    const btn = document.getElementById("btn-confirm");
    btn.disabled = true;
    btn.textContent = "Guardando…";

    await fetch("/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields }),
    });

    btn.textContent = "✓ Confirmado — puedes cerrar esta ventana";
    btn.style.background = "#6b7280";
  });
});
