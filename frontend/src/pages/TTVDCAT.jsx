import { useEffect, useRef, useState } from "react";
import api from "../api/axios";
import BarDeepDiveOverlay from "../components/BarDeepDiveOverlay";
import { PageTitle } from "../components/HelpPOCHeader";
import "./GridPage.css";

export default function TTVDCAT() {
  const containerRef = useRef(null);
  const [categories, setCategories] = useState([]);
  const [selected, setSelected] = useState(null);
  const [inserting, setInserting] = useState(false);
  const [form, setForm] = useState({ category_code: "", description: "", system_required_ind: "N" });
  const [banner, setBanner] = useState(null);

  const load = () => {
    api.get("/categories").then(({ data }) => setCategories(data));
  };

  useEffect(load, []);

  const handleInsert = async (e) => {
    e.preventDefault();
    setBanner(null);
    try {
      await api.post("/categories", form);
      setForm({ category_code: "", description: "", system_required_ind: "N" });
      setInserting(false);
      load();
    } catch (err) {
      setBanner({ type: "error", text: err?.response?.data?.error || "Could not save category." });
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    setBanner(null);
    try {
      await api.delete(`/categories/${selected}`);
      setSelected(null);
      load();
    } catch (err) {
      setBanner({ type: "error", text: err?.response?.data?.error || "Could not delete category." });
    }
  };

  return (
    <div className="grid-page" ref={containerRef}>
      <PageTitle code="TTVDCAT" subtitle="Detail Category Code Validation" />

      {banner && <div className={`grid-banner grid-banner--${banner.type}`}>{banner.text}</div>}

      <div className="grid-card">
        <div className="grid-toolbar">
          <span className="grid-toolbar-title">DETAIL CATEGORY CODE VALIDATION</span>
          <div className="grid-toolbar-actions">
            <button className="grid-toolbar-btn" onClick={() => setInserting((v) => !v)}>+ Insert</button>
            <button className="grid-toolbar-btn" disabled={!selected} onClick={handleDelete}>- Delete</button>
          </div>
        </div>

        <div className="grid-table-wrap">
          <table className="grid-table">
            <thead>
              <tr>
                <th>Code<span className="grid-required">*</span></th>
                <th>Description<span className="grid-required">*</span></th>
                <th>System Required</th>
              </tr>
            </thead>
            <tbody>
              {inserting && (
                <tr className="grid-insert-row">
                  <td>
                    <input
                      maxLength={4}
                      value={form.category_code}
                      onChange={(e) => setForm({ ...form, category_code: e.target.value.toUpperCase() })}
                      placeholder="e.g. FA"
                    />
                  </td>
                  <td>
                    <input
                      maxLength={60}
                      value={form.description}
                      onChange={(e) => setForm({ ...form, description: e.target.value })}
                      placeholder="Description"
                    />
                  </td>
                  <td style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="checkbox"
                      checked={form.system_required_ind === "Y"}
                      onChange={(e) => setForm({ ...form, system_required_ind: e.target.checked ? "Y" : "N" })}
                    />
                    <button className="grid-toolbar-btn" onClick={handleInsert}>Save</button>
                  </td>
                </tr>
              )}
              {categories.map((c) => (
                <tr
                  key={c.category_code}
                  className={selected === c.category_code ? "grid-row--selected" : ""}
                  onClick={() => setSelected(c.category_code)}
                >
                  <td>{c.category_code}</td>
                  <td>{c.description}</td>
                  <td>
                    <input type="checkbox" checked={c.system_required_ind === "Y"} readOnly disabled />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid-footer">
          <span>1 of 1</span>
          <span>Record {categories.length === 0 ? 0 : 1} of {categories.length}</span>
        </div>
      </div>

      <BarDeepDiveOverlay containerRef={containerRef} />
    </div>
  );
}
