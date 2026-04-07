document.addEventListener("DOMContentLoaded", () => {
  const initial = JSON.parse(document.getElementById("initial-data").textContent);
  let currentStep = 1;
  let imagesCache = null;

  // ── Utilidades ──────────────────────────────────────
  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function fmtNum(n) {
    return Number(n).toLocaleString("es-CO");
  }

  // ── Navegación wizard ───────────────────────────────
  const steps = ["step-data", "step-products", "step-photos"];
  const stepEls = document.querySelectorAll(".wizard-step");

  function showStep(n) {
    currentStep = n;
    steps.forEach((id, i) => {
      const el = document.getElementById(id);
      el.classList.toggle("hidden", i + 1 !== n);
    });
    stepEls.forEach(el => {
      const s = parseInt(el.dataset.step);
      el.classList.toggle("active", s === n);
      el.classList.toggle("completed", s < n);
    });
  }

  // ══════════════════════════════════════════════════════
  // STEP 1: Datos
  // ══════════════════════════════════════════════════════
  const fieldsEl = document.getElementById("fields");

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

  // Poblar datos iniciales
  Object.entries(initial.data).forEach(([k, v]) => addRow(k, v ?? ""));

  document.getElementById("btn-add-field").addEventListener("click", () => {
    const row = addRow();
    row.querySelector(".key").focus();
  });

  function collectFields() {
    const fields = {};
    fieldsEl.querySelectorAll(".field-row").forEach(row => {
      const k = row.querySelector(".key").value.trim();
      const v = row.querySelector(".val").value.trim();
      if (k) fields[k] = v === "" ? null : v;
    });
    return fields;
  }

  document.getElementById("btn-next-1").addEventListener("click", async () => {
    const btn = document.getElementById("btn-next-1");
    btn.disabled = true;
    btn.textContent = "Guardando…";

    const fields = collectFields();
    await fetch("/confirm/data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields }),
    });

    btn.disabled = false;
    btn.textContent = "Siguiente";
    showStep(2);
  });

  // ══════════════════════════════════════════════════════
  // STEP 2: Productos
  // ══════════════════════════════════════════════════════
  const tbody = document.getElementById("products-body");
  let productCounter = 0;

  function recalcRow(row) {
    const vrInput = row.querySelector(".vr-uni");
    const val = parseInt(vrInput.value) || 0;
    const iva = Math.round(val * 0.19);
    const total = val + iva;
    row.querySelector(".iva-cell").textContent = fmtNum(iva);
    row.querySelector(".total-cell").textContent = fmtNum(total);
  }

  function addProductRow(product = {}) {
    productCounter++;
    const item = product.item || productCounter;
    const tr = document.createElement("tr");
    tr.className = "product-row";
    tr.innerHTML = `
      <td class="item-cell">${item}</td>
      <td><input type="number" class="qty" value="${product.qty ?? 1}" min="1"></td>
      <td><input type="text" class="desc" value="${escHtml(product.desc ?? "")}"></td>
      <td><input type="text" class="unit" value="${escHtml(product.unit ?? "und")}"></td>
      <td><input type="number" class="vr-uni" value="${product.vr_uni_inc ?? 0}" min="0"></td>
      <td class="iva-cell computed">0</td>
      <td class="total-cell computed">0</td>
      <td><button class="del" title="Eliminar">✕</button></td>
    `;

    tr.querySelector(".vr-uni").addEventListener("input", () => recalcRow(tr));
    tr.querySelector(".del").addEventListener("click", () => {
      tr.remove();
      renumberProducts();
    });
    tbody.appendChild(tr);
    recalcRow(tr);
    return tr;
  }

  function renumberProducts() {
    tbody.querySelectorAll(".product-row").forEach((tr, i) => {
      tr.querySelector(".item-cell").textContent = i + 1;
    });
  }

  // Poblar productos iniciales
  initial.products.forEach(p => addProductRow(p));

  document.getElementById("btn-add-product").addEventListener("click", () => {
    addProductRow();
  });

  function collectProducts() {
    const products = [];
    tbody.querySelectorAll(".product-row").forEach((tr, i) => {
      products.push({
        item: i + 1,
        qty: parseInt(tr.querySelector(".qty").value) || 1,
        desc: tr.querySelector(".desc").value.trim(),
        unit: tr.querySelector(".unit").value.trim() || "und",
        vr_uni_inc: parseInt(tr.querySelector(".vr-uni").value) || 0,
      });
    });
    return products;
  }

  document.getElementById("btn-back-2").addEventListener("click", () => showStep(1));

  document.getElementById("btn-next-2").addEventListener("click", async () => {
    const btn = document.getElementById("btn-next-2");
    btn.disabled = true;
    btn.textContent = "Guardando…";

    const products = collectProducts();
    await fetch("/confirm/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ products }),
    });

    // Cargar imágenes si no están en cache
    if (!imagesCache) {
      const res = await fetch("/images");
      const data = await res.json();
      imagesCache = data.images;
    }
    populatePhotos();

    btn.disabled = false;
    btn.textContent = "Siguiente";
    showStep(3);
  });

  // ══════════════════════════════════════════════════════
  // STEP 3: Fotos
  // ══════════════════════════════════════════════════════
  const photoList = document.getElementById("photo-list");

  function populatePhotos() {
    if (photoList.children.length > 0) return; // ya poblado

    const imgs = imagesCache || [];
    const captions = initial.captions || [];

    // Crear tarjetas de fotos
    imgs.forEach((b64, i) => {
      const cap = captions[i] || { index: i, caption: "" };
      const div = document.createElement("div");
      div.className = "photo-item";
      div.innerHTML = `
        <img src="data:image/png;base64,${b64}" alt="Foto ${i + 1}">
        <div class="photo-edit">
          <label>Foto ${i + 1}</label>
          <textarea class="caption" data-index="${cap.index}" rows="3">${escHtml(cap.caption)}</textarea>
        </div>
      `;
      photoList.appendChild(div);
    });

    // Si no hay imágenes, mostrar mensaje
    if (imgs.length === 0) {
      photoList.innerHTML = '<p class="hint">No se encontraron imágenes en el documento.</p>';
    }
  }

  document.getElementById("btn-back-3").addEventListener("click", () => showStep(2));

  document.getElementById("btn-confirm").addEventListener("click", async () => {
    const btn = document.getElementById("btn-confirm");
    btn.disabled = true;
    btn.textContent = "Guardando…";

    const fotos = [];
    photoList.querySelectorAll(".caption").forEach(ta => {
      fotos.push({
        index: parseInt(ta.dataset.index),
        caption: ta.value.trim(),
      });
    });

    await fetch("/confirm/photos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fotos }),
    });

    btn.textContent = "✓ Confirmado — puedes cerrar esta ventana";
    btn.style.background = "#6b7280";
  });

  // Iniciar en paso 1
  showStep(1);
});
