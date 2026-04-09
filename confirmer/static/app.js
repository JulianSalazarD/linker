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
      document.getElementById(id).classList.toggle("hidden", i + 1 !== n);
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
    addRow().querySelector(".key").focus();
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
    await fetch("/confirm/data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields: collectFields() }),
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
    const val = parseInt(row.querySelector(".vr-uni").value) || 0;
    const iva = Math.round(val * 0.19);
    row.querySelector(".iva-cell").textContent = fmtNum(iva);
    row.querySelector(".total-cell").textContent = fmtNum(val + iva);
  }

  function addProductRow(product = {}) {
    productCounter++;
    const tr = document.createElement("tr");
    tr.className = "product-row";
    tr.innerHTML = `
      <td class="item-cell">${product.item || productCounter}</td>
      <td><input type="number" class="qty" value="${product.qty ?? 1}" min="1"></td>
      <td><textarea class="desc" rows="2">${escHtml(product.desc ?? "")}</textarea></td>
      <td><input type="text" class="unit" value="${escHtml(product.unit ?? "und")}"></td>
      <td><input type="number" class="vr-uni" value="${product.vr_uni_inc ?? 0}" min="0"></td>
      <td class="iva-cell computed">0</td>
      <td class="total-cell computed">0</td>
      <td><button class="del" title="Eliminar">✕</button></td>
    `;
    tr.querySelector(".vr-uni").addEventListener("input", () => recalcRow(tr));
    tr.querySelector(".del").addEventListener("click", () => { tr.remove(); renumberProducts(); });
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

  document.getElementById("btn-add-product").addEventListener("click", () => addProductRow());

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
    await fetch("/confirm/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ products: collectProducts() }),
    });
    if (!imagesCache) {
      const [thumbRes, fullRes] = await Promise.all([fetch("/images"), fetch("/images/full")]);
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
        <button class="btn-edit-img" title="Editar imagen">&#9998;</button>
        <button class="btn-move-up" title="Mover arriba">&#9650;</button>
        <button class="btn-move-down" title="Mover abajo">&#9660;</button>
        <button class="del" title="Eliminar">✕</button>
      </div>
    `;

    // Abrir editor al hacer clic en thumbnail o botón editar
    div.querySelector("img").addEventListener("click", () => openEditor(div));
    div.querySelector(".btn-edit-img").addEventListener("click", () => openEditor(div));

    div.querySelector(".btn-move-up").addEventListener("click", () => {
      const prev = div.previousElementSibling;
      if (prev) { photoList.insertBefore(div, prev); renumberPhotos(); }
    });
    div.querySelector(".btn-move-down").addEventListener("click", () => {
      const next = div.nextElementSibling;
      if (next) { photoList.insertBefore(next, div); renumberPhotos(); }
    });
    div.querySelector(".del").addEventListener("click", () => { div.remove(); renumberPhotos(); });

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
      photoList.appendChild(createPhotoItem(b64, fullImgs[i] || b64, cap.caption, i));
    });
    if (imgs.length === 0) {
      photoList.innerHTML = '<p class="hint">No se encontraron imágenes en el documento.</p>';
    }
  }

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

  // ══════════════════════════════════════════════════════
  // IMAGE EDITOR (modal con canvas)
  // ══════════════════════════════════════════════════════

  const modal = document.getElementById("editor-modal");
  const canvas = document.getElementById("editor-canvas");
  const ctx = canvas.getContext("2d");
  const canvasWrap = document.getElementById("editor-canvas-wrap");

  let editorPhotoDiv = null;   // referencia al photo-item que se edita
  let baseImage = null;        // Image() con la foto original
  let strokes = [];            // [{tool, color, width, points|start+end}]
  let placedOverlays = [];     // [{img:HTMLImageElement, x, y, w, h, el:HTMLDivElement}]
  let currentTool = "free";
  let currentColor = "#ef4444";
  let currentWidth = 3;
  let isDrawing = false;
  let drawStart = null;
  let currentPoints = [];
  let overlaysData = null;     // cache de fetch /overlays

  // ── Toolbar events ──────────────────────────────────
  document.querySelectorAll(".tool-group .tool-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tool-group .tool-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentTool = btn.dataset.tool;
    });
  });

  document.querySelectorAll(".color-dot").forEach(dot => {
    dot.addEventListener("click", () => {
      document.querySelectorAll(".color-dot").forEach(d => d.classList.remove("active"));
      dot.classList.add("active");
      currentColor = dot.dataset.color;
    });
  });

  document.getElementById("stroke-width").addEventListener("input", (e) => {
    currentWidth = parseInt(e.target.value);
  });

  document.getElementById("btn-undo").addEventListener("click", undoStroke);
  document.getElementById("btn-editor-cancel").addEventListener("click", () => closeEditor(false));
  document.getElementById("btn-editor-save").addEventListener("click", () => closeEditor(true));

  // ── Open/close editor ───────────────────────────────
  function openEditor(photoDiv) {
    editorPhotoDiv = photoDiv;
    strokes = [];
    placedOverlays = [];

    // Limpiar overlays anteriores del DOM
    canvasWrap.querySelectorAll(".overlay-placed").forEach(el => el.remove());

    // Cargar imagen base desde fullB64
    baseImage = new Image();
    baseImage.onload = () => {
      canvas.width = baseImage.width;
      canvas.height = baseImage.height;
      renderCanvas();
      modal.classList.remove("hidden");
    };
    baseImage.src = "data:image/png;base64," + photoDiv.dataset.fullB64;

    // Cargar overlays si no están en cache
    loadOverlays();
  }

  function closeEditor(save) {
    if (save) {
      const exportB64 = exportCanvas();
      editorPhotoDiv.dataset.fullB64 = exportB64;
      // Actualizar thumbnail visible
      editorPhotoDiv.querySelector("img").src = "data:image/png;base64," + exportB64;
    }
    // Limpiar overlays del DOM
    canvasWrap.querySelectorAll(".overlay-placed").forEach(el => el.remove());
    placedOverlays = [];
    modal.classList.add("hidden");
  }

  // ── Render canvas ───────────────────────────────────
  function renderCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(baseImage, 0, 0);
    strokes.forEach(s => drawStroke(s));
  }

  function drawStroke(s) {
    ctx.strokeStyle = s.color;
    ctx.lineWidth = s.width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (s.tool === "free") {
      if (s.points.length < 2) return;
      ctx.beginPath();
      ctx.moveTo(s.points[0].x, s.points[0].y);
      for (let i = 1; i < s.points.length; i++) {
        ctx.lineTo(s.points[i].x, s.points[i].y);
      }
      ctx.stroke();
    } else if (s.tool === "rect") {
      const x = Math.min(s.start.x, s.end.x);
      const y = Math.min(s.start.y, s.end.y);
      const w = Math.abs(s.end.x - s.start.x);
      const h = Math.abs(s.end.y - s.start.y);
      ctx.strokeRect(x, y, w, h);
    } else if (s.tool === "line") {
      ctx.beginPath();
      ctx.moveTo(s.start.x, s.start.y);
      ctx.lineTo(s.end.x, s.end.y);
      ctx.stroke();
    }
  }

  function undoStroke() {
    if (strokes.length > 0) {
      strokes.pop();
      renderCanvas();
    }
  }

  // ── Canvas mouse → image coords ────────────────────
  function canvasCoords(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  }

  // ── Canvas drawing events ───────────────────────────
  canvas.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    isDrawing = true;
    const pt = canvasCoords(e);
    drawStart = pt;
    currentPoints = [pt];
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!isDrawing) return;
    const pt = canvasCoords(e);

    if (currentTool === "free") {
      currentPoints.push(pt);
      // Dibujar incrementalmente para fluidez
      ctx.strokeStyle = currentColor;
      ctx.lineWidth = currentWidth;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      const prev = currentPoints[currentPoints.length - 2];
      ctx.beginPath();
      ctx.moveTo(prev.x, prev.y);
      ctx.lineTo(pt.x, pt.y);
      ctx.stroke();
    } else {
      // Preview para rect/line: redibujar todo + preview
      renderCanvas();
      const preview = { tool: currentTool, color: currentColor, width: currentWidth, start: drawStart, end: pt };
      drawStroke(preview);
    }
  });

  canvas.addEventListener("mouseup", (e) => {
    if (!isDrawing) return;
    isDrawing = false;
    const pt = canvasCoords(e);

    if (currentTool === "free") {
      currentPoints.push(pt);
      strokes.push({ tool: "free", color: currentColor, width: currentWidth, points: [...currentPoints] });
    } else {
      strokes.push({ tool: currentTool, color: currentColor, width: currentWidth, start: drawStart, end: pt });
    }
    renderCanvas();
  });

  canvas.addEventListener("mouseleave", () => {
    if (isDrawing && currentTool === "free") {
      strokes.push({ tool: "free", color: currentColor, width: currentWidth, points: [...currentPoints] });
      isDrawing = false;
      renderCanvas();
    }
  });

  // ── Overlays (stickers) ─────────────────────────────
  async function loadOverlays() {
    const grid = document.getElementById("overlay-grid");
    if (overlaysData) {
      // ya poblado
      return;
    }
    grid.innerHTML = '<span style="color:#94a3b8;font-size:12px;padding:8px">Cargando…</span>';
    const res = await fetch("/overlays");
    overlaysData = (await res.json()).overlays;
    grid.innerHTML = "";

    if (overlaysData.length === 0) {
      grid.innerHTML = '<span style="color:#94a3b8;font-size:12px;padding:8px">Sin stickers</span>';
      return;
    }

    overlaysData.forEach(ov => {
      const card = document.createElement("div");
      card.className = "overlay-card";
      card.innerHTML = `
        <img class="overlay-thumb" src="data:${ov.mime};base64,${ov.data}" alt="${escHtml(ov.name)}">
        <span class="overlay-name">${escHtml(ov.name)}</span>
      `;
      card.querySelector("img").addEventListener("click", () => {
        addOverlayToCanvas(ov);
      });
      grid.appendChild(card);
    });
  }

  function addOverlayToCanvas(ov) {
    const img = new Image();
    img.src = `data:${ov.mime};base64,${ov.data}`;
    img.onload = () => {
      // Tamaño inicial: 100px de ancho, proporcional
      const w = 100;
      const h = (img.height / img.width) * w;
      // Posición inicial: centro del canvas visible
      const rect = canvas.getBoundingClientRect();
      const x = rect.width / 2 - w / 2;
      const y = rect.height / 2 - h / 2;

      const el = document.createElement("div");
      el.className = "overlay-placed";
      el.style.left = x + "px";
      el.style.top = y + "px";
      el.style.width = w + "px";
      el.style.height = h + "px";
      el.innerHTML = `<img src="${img.src}"><button class="overlay-del">✕</button>`;

      const entry = { imgEl: img, el, x, y, w, h };
      placedOverlays.push(entry);

      el.querySelector(".overlay-del").addEventListener("click", (e) => {
        e.stopPropagation();
        el.remove();
        placedOverlays = placedOverlays.filter(o => o.el !== el);
      });

      // Drag
      makeDraggable(el, entry);

      canvasWrap.appendChild(el);
    };
  }

  function makeDraggable(el, entry) {
    let dragX, dragY;

    el.addEventListener("mousedown", (e) => {
      if (e.target.classList.contains("overlay-del")) return;
      e.preventDefault();
      e.stopPropagation();
      dragX = e.clientX - el.offsetLeft;
      dragY = e.clientY - el.offsetTop;

      function onMove(ev) {
        const newX = ev.clientX - dragX;
        const newY = ev.clientY - dragY;
        el.style.left = newX + "px";
        el.style.top = newY + "px";
        entry.x = newX;
        entry.y = newY;
      }
      function onUp() {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      }
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }

  // ── Export: fusionar canvas + overlays ───────────────
  function exportCanvas() {
    // Crear canvas temporal a tamaño real
    const tmpCanvas = document.createElement("canvas");
    tmpCanvas.width = baseImage.width;
    tmpCanvas.height = baseImage.height;
    const tmpCtx = tmpCanvas.getContext("2d");

    // Dibujar imagen base + strokes
    tmpCtx.drawImage(baseImage, 0, 0);
    strokes.forEach(s => {
      tmpCtx.strokeStyle = s.color;
      tmpCtx.lineWidth = s.width;
      tmpCtx.lineCap = "round";
      tmpCtx.lineJoin = "round";

      if (s.tool === "free") {
        if (s.points.length < 2) return;
        tmpCtx.beginPath();
        tmpCtx.moveTo(s.points[0].x, s.points[0].y);
        for (let i = 1; i < s.points.length; i++) {
          tmpCtx.lineTo(s.points[i].x, s.points[i].y);
        }
        tmpCtx.stroke();
      } else if (s.tool === "rect") {
        const x = Math.min(s.start.x, s.end.x);
        const y = Math.min(s.start.y, s.end.y);
        const w = Math.abs(s.end.x - s.start.x);
        const h = Math.abs(s.end.y - s.start.y);
        tmpCtx.strokeRect(x, y, w, h);
      } else if (s.tool === "line") {
        tmpCtx.beginPath();
        tmpCtx.moveTo(s.start.x, s.start.y);
        tmpCtx.lineTo(s.end.x, s.end.y);
        tmpCtx.stroke();
      }
    });

    // Dibujar overlays: convertir posición CSS → coordenadas del canvas
    const canvasRect = canvas.getBoundingClientRect();
    const scaleX = baseImage.width / canvasRect.width;
    const scaleY = baseImage.height / canvasRect.height;

    placedOverlays.forEach(ov => {
      const dx = ov.x * scaleX;
      const dy = ov.y * scaleY;
      const dw = ov.w * scaleX;
      const dh = ov.h * scaleY;
      tmpCtx.drawImage(ov.imgEl, dx, dy, dw, dh);
    });

    return tmpCanvas.toDataURL("image/png").split(",")[1];
  }

  // Iniciar en paso 1
  showStep(1);
});
