document.addEventListener("DOMContentLoaded", () => {
  const initial = JSON.parse(document.getElementById("initial-data").textContent);
  let currentStep = 1;
  let imagesCache = null;       // thumbnails para mostrar
  let imagesFullCache = null;    // full-size para el docx

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
      <td><textarea class="desc" rows="2">${escHtml(product.desc ?? "")}</textarea></td>
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

    // Cargar imágenes si no están en cache (thumb + full en paralelo)
    if (!imagesCache) {
      const [thumbRes, fullRes] = await Promise.all([
        fetch("/images"),
        fetch("/images/full"),
      ]);
      const thumbData = await thumbRes.json();
      const fullData = await fullRes.json();
      imagesCache = thumbData.images;
      imagesFullCache = fullData.images;
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
  let photosPopulated = false;

  function createPhotoItem(b64, fullB64, caption, index) {
    const div = document.createElement("div");
    div.className = "photo-item";
    div.dataset.index = index;
    div.dataset.fullB64 = fullB64;
    div.innerHTML = `
      <img src="data:image/png;base64,${b64}" alt="Foto ${index + 1}">
      <div class="photo-edit">
        <label>Foto ${index + 1}</label>
        <textarea class="caption" rows="3">${escHtml(caption)}</textarea>
      </div>
      <div class="photo-actions">
        <button class="btn-move-up" title="Mover arriba">▲</button>
        <button class="btn-move-down" title="Mover abajo">▼</button>
        <button class="del" title="Eliminar">✕</button>
      </div>
    `;

    div.querySelector(".btn-move-up").addEventListener("click", () => {
      const prev = div.previousElementSibling;
      if (prev) {
        photoList.insertBefore(div, prev);
        renumberPhotos();
      }
    });

    div.querySelector(".btn-move-down").addEventListener("click", () => {
      const next = div.nextElementSibling;
      if (next) {
        photoList.insertBefore(next, div);
        renumberPhotos();
      }
    });

    div.querySelector(".del").addEventListener("click", () => {
      div.remove();
      renumberPhotos();
    });

    return div;
  }

  function renumberPhotos() {
    photoList.querySelectorAll(".photo-item").forEach((div, i) => {
      div.dataset.index = i;
      div.querySelector("label").textContent = `Foto ${i + 1}`;
    });
  }

  function populatePhotos() {
    if (photosPopulated) return;
    photosPopulated = true;

    const imgs = imagesCache || [];
    const captions = initial.captions || [];

    const fullImgs = imagesFullCache || [];
    imgs.forEach((b64, i) => {
      const cap = captions[i] || { index: i, caption: "" };
      const full = fullImgs[i] || b64;
      photoList.appendChild(createPhotoItem(b64, full, cap.caption, i));
    });

    if (imgs.length === 0) {
      photoList.innerHTML = '<p class="hint">No se encontraron imágenes en el documento.</p>';
    }
  }

  // Insertar imagen desde archivo local
  document.getElementById("btn-add-photo").addEventListener("click", () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.multiple = true;
    input.addEventListener("change", () => {
      Array.from(input.files).forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const fullB64 = e.target.result.split(",")[1];
          const idx = photoList.querySelectorAll(".photo-item").length;
          photoList.appendChild(createPhotoItem(fullB64, fullB64, "", idx));
          renumberPhotos();
        };
        reader.readAsDataURL(file);
      });
    });
    input.click();
  });

  document.getElementById("btn-back-3").addEventListener("click", () => showStep(2));

  document.getElementById("btn-confirm").addEventListener("click", async () => {
    const btn = document.getElementById("btn-confirm");
    btn.disabled = true;
    btn.textContent = "Guardando…";

    const fotos = [];
    photoList.querySelectorAll(".photo-item").forEach((div, i) => {
      fotos.push({
        index: i,
        caption: div.querySelector(".caption").value.trim(),
        image_b64: div.dataset.fullB64,
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
