import { useEffect, useRef, useState } from "react";
import api from "../api/axios";
import BarDeepDiveOverlay from "../components/BarDeepDiveOverlay";
import { PageTitle } from "../components/HelpPOCHeader";
import "./GridPage.css";

const emptyForm = {
  detail_code: "",
  description: "",
  type_code: "C",
  category_code: "",
  priority_no: 0,
};

export default function TSADETC() {
  const containerRef = useRef(null);
  const [detailCodes, setDetailCodes] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selected, setSelected] = useState(null);
  const [inserting, setInserting] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [banner, setBanner] = useState(null);

  const load = () => {
    api.get("/detail-codes").then(({ data }) => setDetailCodes(data));
    api.get("/categories?active=Y").then(({ data }) => setCategories(data));
  };

  useEffect(load, []);

  const handleInsert = async (e) => {
    e.preventDefault();
    setBanner(null);
    try {
      await api.post("/detail-codes", { ...form, priority_no: Number(form.priority_no) });
      setForm(emptyForm);
      setInserting(false);
      load();
    } catch (err) {
      setBanner({ type: "error", text: err?.response?.data?.error || "Could not save detail code." });
    }
  };

  const handleDelete = async () => {
    if (!selected) return;
    setBanner(null);
    try {
      await api.delete(`/detail-codes/${selected}`);
      setSelected(null);
      load();
    } catch (err) {
      setBanner({ type: "error", text: err?.response?.data?.error || "Could not delete detail code." });
    }
  };

  return (
    <div className="grid-page" ref={containerRef}>
      <PageTitle code="TSADETC" subtitle="Detail Code Control Form - Student" />

      {banner && <div className={`grid-banner grid-banner--${banner.type}`}>{banner.text}</div>}

      <div className="grid-card">
        <div className="grid-toolbar">
          <span className="grid-toolbar-title">DETAIL CODE CONTROL FORM - STUDENT</span>
          <div className="grid-toolbar-actions">
            <button className="grid-toolbar-btn" onClick={() => setInserting((v) => !v)}>+ Insert</button>
            <button className="grid-toolbar-btn" disabled={!selected} onClick={handleDelete}>- Delete</button>
          </div>
        </div>

        <div className="grid-table-wrap">
          <table className="grid-table">
            <thead>
              <tr>
                <th>Detail Code<span className="grid-required">*</span></th>
                <th>Detail Code Description<span className="grid-required">*</span></th>
                <th>Type<span className="grid-required">*</span></th>
                <th>Category<span className="grid-required">*</span></th>
                <th>Priority<span className="grid-required">*</span></th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {inserting && (
                <tr className="grid-insert-row">
                  <td>
                    <input maxLength={4} value={form.detail_code}
                      onChange={(e) => setForm({ ...form, detail_code: e.target.value.toUpperCase() })} />
                  </td>
                  <td>
                    <input maxLength={60} value={form.description}
                      onChange={(e) => setForm({ ...form, description: e.target.value })} />
                  </td>
                  <td>
                    <select value={form.type_code} onChange={(e) => setForm({ ...form, type_code: e.target.value })}>
                      <option value="C">C - Charge</option>
                      <option value="P">P - Payment</option>
                    </select>
                  </td>
                  <td>
                    <select value={form.category_code} onChange={(e) => setForm({ ...form, category_code: e.target.value })}>
                      <option value="">Select...</option>
                      {categories.map((c) => (
                        <option key={c.category_code} value={c.category_code}>{c.category_code}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input type="number" min={0} max={999} value={form.priority_no}
                      onChange={(e) => setForm({ ...form, priority_no: e.target.value })} />
                  </td>
                  <td>
                    <button className="grid-toolbar-btn" onClick={handleInsert}>Save</button>
                  </td>
                </tr>
              )}
              {detailCodes.map((d) => (
                <tr
                  key={d.detail_code}
                  className={selected === d.detail_code ? "grid-row--selected" : ""}
                  onClick={() => setSelected(d.detail_code)}
                >
                  <td>{d.active_ind === "N" ? <span className="grid-inactive">{d.detail_code}</span> : d.detail_code}</td>
                  <td>{d.description}</td>
                  <td>{d.type_code}</td>
                  <td>{d.category_code}</td>
                  <td>{String(d.priority_no).padStart(3, "0")}</td>
                  <td>{d.active_ind === "Y" ? "Active" : <span className="grid-inactive">Inactive</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid-footer">
          <span>1 of 1</span>
          <span>Record {detailCodes.length === 0 ? 0 : 1} of {detailCodes.length}</span>
        </div>
      </div>

      <BarDeepDiveOverlay containerRef={containerRef} />
    </div>
  );
}
