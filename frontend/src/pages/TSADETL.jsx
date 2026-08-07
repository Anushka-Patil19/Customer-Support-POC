import { useEffect, useRef, useState } from "react";
import api from "../api/axios";
import BarDeepDiveOverlay from "../components/BarDeepDiveOverlay";
import { PageTitle } from "../components/HelpPOCHeader";
import "./GridPage.css";
import "./TSADETL.css";

const TABS = ["Charges/Payments", "Deposits", "Memos"];

export default function TSADETL() {
  const containerRef = useRef(null);
  const [idInput, setIdInput] = useState("D00010001");
  const [person, setPerson] = useState(null);
  const [personError, setPersonError] = useState(null);
  const [tab, setTab] = useState(TABS[0]);
  const [transactions, setTransactions] = useState([]);
  const [detailCodes, setDetailCodes] = useState([]);
  const [terms, setTerms] = useState([]);
  const [balance, setBalance] = useState(null);
  const [inserting, setInserting] = useState(false);
  const [form, setForm] = useState({ detail_code: "", amount: "", term_code: "" });
  const [banner, setBanner] = useState(null);

  useEffect(() => {
    api.get("/detail-codes?active=Y").then(({ data }) => setDetailCodes(data));
    api.get("/transactions/terms").then(({ data }) => setTerms(data));
  }, []);

  const loadAccount = async (bannerId) => {
    setBanner(null);
    setPersonError(null);
    try {
      const { data } = await api.get(`/transactions/person/${bannerId}`);
      setPerson(data);
      const [txRes, balRes] = await Promise.all([
        api.get("/transactions", { params: { banner_id: bannerId } }),
        api.get("/transactions/balance", { params: { banner_id: bannerId } }),
      ]);
      setTransactions(txRes.data);
      setBalance(balRes.data.balance);
    } catch (err) {
      setPerson(null);
      setTransactions([]);
      setBalance(null);
      const message = err?.response
        ? err.response.data?.error || "Enter a valid active student ID."
        : "Can't reach the backend API -- is it running?";
      setPersonError(message);
    }
  };

  useEffect(() => {
    if (idInput) loadAccount(idInput);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleStartOver = () => {
    setIdInput("");
    setPerson(null);
    setTransactions([]);
    setBalance(null);
    setPersonError(null);
    setInserting(false);
  };

  const handleIdSubmit = (e) => {
    e.preventDefault();
    if (idInput.trim()) loadAccount(idInput.trim().toUpperCase());
  };

  const handleInsert = async (e) => {
    e.preventDefault();
    setBanner(null);
    try {
      await api.post("/transactions", {
        banner_id: person.banner_id,
        detail_code: form.detail_code,
        term_code: form.term_code,
        amount: Number(form.amount),
      });
      setForm({ detail_code: "", amount: "", term_code: "" });
      setInserting(false);
      loadAccount(person.banner_id);
    } catch (err) {
      setBanner({ type: "error", text: err?.response?.data?.error || "Could not save transaction." });
    }
  };

  return (
    <div className="grid-page" ref={containerRef}>
      <PageTitle code="TSADETL" subtitle="Student Account Detail" />

      <div className="grid-card">
        <form className="grid-field-row" onSubmit={handleIdSubmit}>
          <div className="grid-field">
            <label>ID</label>
            <input value={idInput} onChange={(e) => setIdInput(e.target.value.toUpperCase())} placeholder="D00010001" />
          </div>
          <div className="grid-field">
            <label>Name</label>
            <input value={person?.display_name || ""} readOnly disabled />
          </div>
          <div className="grid-field">
            <label>Credit Limit</label>
            <input value={person?.credit_limit ?? ""} readOnly disabled />
          </div>
          <div className="grid-field">
            <label>Holds</label>
            <input value={person?.hold_ind === "Y" ? "AR Hold" : ""} readOnly disabled />
          </div>
          <button type="button" className="grid-toolbar-btn" onClick={handleStartOver}>Start Over</button>
          <button type="submit" className="grid-toolbar-btn">Go</button>
        </form>

        {personError && <div className="grid-banner grid-banner--error" style={{ margin: "0 16px 16px" }}>{personError}</div>}

        <div className="tsl-tabs">
          {TABS.map((t) => (
            <button key={t} className={`tsl-tab${tab === t ? " tsl-tab--active" : ""}`} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </div>

        {tab === "Charges/Payments" && person && (
          <>
            {banner && <div className={`grid-banner grid-banner--${banner.type}`} style={{ margin: "12px 16px 0" }}>{banner.text}</div>}

            <div className="grid-toolbar">
              <span className="grid-toolbar-title">CHARGES/PAYMENTS</span>
              <div className="grid-toolbar-actions">
                <button className="grid-toolbar-btn" onClick={() => setInserting((v) => !v)}>+ Insert</button>
              </div>
            </div>

            <div className="grid-table-wrap">
              <table className="grid-table">
                <thead>
                  <tr>
                    <th>Detail Code<span className="grid-required">*</span></th>
                    <th>Detail Code Description<span className="grid-required">*</span></th>
                    <th>Amount<span className="grid-required">*</span></th>
                    <th>Balance</th>
                    <th>Term<span className="grid-required">*</span></th>
                  </tr>
                </thead>
                <tbody>
                  {inserting && (
                    <tr className="grid-insert-row">
                      <td>
                        <select value={form.detail_code} onChange={(e) => setForm({ ...form, detail_code: e.target.value })}>
                          <option value="">Select...</option>
                          {detailCodes.map((d) => (
                            <option key={d.detail_code} value={d.detail_code}>{d.detail_code}</option>
                          ))}
                        </select>
                      </td>
                      <td>{detailCodes.find((d) => d.detail_code === form.detail_code)?.description || ""}</td>
                      <td>
                        <input type="number" step="0.01" value={form.amount}
                          onChange={(e) => setForm({ ...form, amount: e.target.value })} />
                      </td>
                      <td>—</td>
                      <td>
                        <select value={form.term_code} onChange={(e) => setForm({ ...form, term_code: e.target.value })}>
                          <option value="">Select...</option>
                          {terms.map((t) => (
                            <option key={t.term_code} value={t.term_code}>{t.term_code}</option>
                          ))}
                        </select>
                        <button className="grid-toolbar-btn" style={{ marginTop: 6 }} onClick={handleInsert}>Save</button>
                      </td>
                    </tr>
                  )}
                  {transactions.map((t) => (
                    <tr key={t.transaction_id}>
                      <td>{t.detail_code}</td>
                      <td>{t.detail_code_description}</td>
                      <td>{t.entry_amount.toFixed(2)}</td>
                      <td>{t.open_balance.toFixed(2)}</td>
                      <td>{t.term_code}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="grid-footer">
              <span>1 of 1</span>
              <span>Record {transactions.length === 0 ? 0 : 1} of {transactions.length}</span>
            </div>
          </>
        )}

        {tab !== "Charges/Payments" && (
          <div className="grid-banner grid-banner--info" style={{ margin: 16 }}>
            {tab} is not part of this POC's scope -- only Charges/Payments is simulated.
          </div>
        )}

        {person && (
          <div className="tsl-balance-section">
            <div className="grid-toolbar-title" style={{ padding: "12px 16px 0" }}>BALANCE DETAILS</div>
            <div className="grid-field-row">
              <div className="grid-field">
                <label>Account Balance</label>
                <input value={balance !== null ? balance.toFixed(2) : ""} readOnly disabled />
              </div>
            </div>
          </div>
        )}

        <div className="tsl-save-bar">
          <button
            className="grid-toolbar-btn tsl-save-btn"
            disabled={!person}
            onClick={() => setBanner({ type: "info", text: "Charges/payments are saved as soon as you insert them -- there is nothing pending." })}
          >
            Save
          </button>
        </div>
      </div>

      <BarDeepDiveOverlay containerRef={containerRef} context={person ? { banner_id: person.banner_id } : undefined} />
    </div>
  );
}
