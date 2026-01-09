/* ALK-VisDock frontend (no build step)
   Expects:
     - manifest.json
     - data/molecules.json
     - assets/* (images, structures)
*/

function esc(s) {
  return (s || "").toString()
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;");
}

async function fetchJSON(path) {
  const r = await fetch(path, { cache: "no-cache" });
  if (!r.ok) throw new Error(`Failed to load ${path}: ${r.status}`);
  return await r.json();
}

let VIEWER = null;
let MANIFEST = null;
let MOLECULES = [];

function viewerSetCartoon() {
  if (!VIEWER) return;
  VIEWER.setStyle({}, { cartoon: {} });
  if (MANIFEST && MANIFEST.highlight_resi) {
    for (const r of MANIFEST.highlight_resi) {
      VIEWER.setStyle({ resi: r }, { stick: {} });
    }
  }
  VIEWER.render();
}

function viewerSetSurface() {
  if (!VIEWER) return;
  VIEWER.setStyle({}, { cartoon: { opacity: 0.2 } });
  VIEWER.addSurface($3Dmol.SurfaceType.VDW, { opacity: 0.85 });
  VIEWER.render();
}

function viewerReset() {
  if (!VIEWER) return;
  VIEWER.zoomTo();
  VIEWER.render();
}

function loadPoseIntoViewer(posePath) {
  // posePath is a relative path under assets/poses/... saved during build
  if (!VIEWER) return;
  const url = posePath;
  fetch(url)
    .then(r => r.text())
    .then(txt => {
      // Clear ligand models only; keep the receptor as first model.
      // Simpler: clear all and reload receptor + ligand.
      VIEWER.removeAllModels();

      // Load receptor
      if (MANIFEST && MANIFEST.structure && MANIFEST.structure.path) {
        return fetch(MANIFEST.structure.path)
          .then(rr => rr.text())
          .then(structTxt => ({ structTxt, poseTxt: txt }));
      }
      return ({ structTxt: "", poseTxt: txt });
    })
    .then(({ structTxt, poseTxt }) => {
      if (structTxt) {
        const fmt = (MANIFEST.structure.format || "mmcif").toLowerCase();
        VIEWER.addModel(structTxt, fmt);
        viewerSetCartoon();
      }
      // Docked pose: PDB is easiest for 3Dmol
      VIEWER.addModel(poseTxt, "pdb");
      // Style ligand as sticks
      const last = VIEWER.getModel(VIEWER.getNumModels() - 1);
      last.setStyle({}, { stick: {} });
      VIEWER.zoomTo();
      VIEWER.render();
    })
    .catch(err => {
      console.error(err);
      alert("Failed to load pose. See console.");
    });
}

function renderCards(filter) {
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  const f = (filter || "").toLowerCase();

  for (const d of MOLECULES) {
    const hay = [d.name, d.smiles, d.pubchem_cid, d.chembl_id, d.formula, d.notes].join(" ").toLowerCase();
    if (f && !hay.includes(f)) continue;

    const img = d.image_png
      ? `<img class="mol" src="${esc(d.image_png)}" alt="${esc(d.name)}" />`
      : `<div style="height:220px; display:flex; align-items:center; justify-content:center; border:1px solid #eee; border-radius:8px; background:#fafafa;">(no image)</div>`;

    const dockLine = d.docking && d.docking.mode
      ? `<div class="muted">Docking: <b>${esc(d.docking.mode)}</b> ${d.docking.best_score ? `(best ${esc(d.docking.best_score)})` : ""}</div>`
      : `<div class="muted">Docking: —</div>`;

    const poseBtn = (d.pose && d.pose.path)
      ? `<button data-pose="${esc(d.pose.path)}">View pose</button>`
      : ``;

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3>${esc(d.name)}</h3>
      <div class="muted">${esc(d.formula || "")}</div>
      ${img}
      ${dockLine}
      <div class="kv">
        <div>PubChem</div><div>${d.pubchem_cid ? esc(d.pubchem_cid) : "—"}</div>
        <div>ChEMBL</div><div>${d.chembl_id ? esc(d.chembl_id) : "—"}</div>
        <div>MW</div><div>${esc(d.mw || "—")}</div>
        <div>XLogP</div><div>${esc(d.xlogp || "—")}</div>
        <div>HBD/HBA</div><div>${esc((d.hbd||"—") + "/" + (d.hba||"—"))}</div>
        <div>TPSA</div><div>${esc(d.tpsa || "—")}</div>
        <div>RotB</div><div>${esc(d.rotb || "—")}</div>
        <div>SMILES</div><div><code>${esc(d.smiles || "—")}</code></div>
      </div>
      ${d.notes ? `<div class="muted" style="margin-top:8px;">${esc(d.notes)}</div>` : ""}
      <div class="btnrow">${poseBtn}</div>
    `;

    // bind pose button
    const btn = card.querySelector("button[data-pose]");
    if (btn) {
      btn.addEventListener("click", () => loadPoseIntoViewer(btn.getAttribute("data-pose")));
    }

    grid.appendChild(card);
  }
}

async function main() {
  MANIFEST = await fetchJSON("manifest.json");
  MOLECULES = await fetchJSON("data/molecules.json");

  // header label
  const pdbLabel = document.getElementById("pdbLabel");
  const hl = (MANIFEST.highlight_resi || []).join(", ");
  pdbLabel.innerHTML = `Structure: <b>${esc(MANIFEST.structure && MANIFEST.structure.label ? MANIFEST.structure.label : "—")}</b> • Highlight residues: ${esc(hl)}`;

  // init viewer
  const el = document.getElementById("viewer");
  VIEWER = $3Dmol.createViewer(el, { backgroundColor: "white" });

  if (MANIFEST.structure && MANIFEST.structure.path) {
    const fmt = (MANIFEST.structure.format || "mmcif").toLowerCase();
    const t = await fetch(MANIFEST.structure.path).then(r => r.text());
    VIEWER.addModel(t, fmt);
    viewerSetCartoon();
    VIEWER.zoomTo();
    VIEWER.render();
  } else {
    VIEWER.addLabel("No structure loaded.", { position: {x:0,y:0,z:0}, backgroundColor: "white" });
    VIEWER.render();
  }

  // viewer buttons
  document.getElementById("styleCartoon").addEventListener("click", viewerSetCartoon);
  document.getElementById("styleSurface").addEventListener("click", viewerSetSurface);
  document.getElementById("resetView").addEventListener("click", viewerReset);

  // search
  const q = document.getElementById("q");
  q.addEventListener("input", (e) => renderCards(e.target.value));

  renderCards("");
}

main().catch(err => {
  console.error(err);
  alert("Failed to load site data. Are you serving over HTTP (not file://)?");
});
