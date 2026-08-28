import { useEffect, useRef, useState } from "react";
import api, { API_ORIGIN } from "../api/axios";
import "./BarDeepDiveOverlay.css";

const MIN_RECT_PX = 10;
const MIN_STRIP_HEIGHT = 22; // just a hair taller than a single line of UI text
const VERTICAL_DEAD_ZONE = 20; // small vertical wobble below this is ignored
const VERTICAL_PADDING = 3; // breathing room once a real vertical drag is detected
const VIEWPORT_MARGIN = 16;
const CHAT_PANEL_WIDTH = 400;

// Horizontal movement always grows the selection. Vertical movement only
// grows it once it exceeds a small dead zone -- so accidental hand wobble
// during a mostly-horizontal drag can't balloon the box, but a deliberate
// drag down/up to cover a taller, multi-line area still works normally.
function stripFromDrag(start, current) {
  const dy = current.y - start.y;
  const realDy = Math.abs(dy) > VERTICAL_DEAD_ZONE ? dy : 0;
  const endY = start.y + realDy;

  let top = Math.min(start.y, endY) - VERTICAL_PADDING;
  let bottom = Math.max(start.y, endY) + VERTICAL_PADDING;
  if (bottom - top < MIN_STRIP_HEIGHT) {
    const mid = (top + bottom) / 2;
    top = mid - MIN_STRIP_HEIGHT / 2;
    bottom = mid + MIN_STRIP_HEIGHT / 2;
  }

  return {
    left: Math.min(start.x, current.x),
    right: Math.max(start.x, current.x),
    top,
    bottom,
  };
}

function rectsIntersect(a, b) {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

// An element's own text, ignoring text that belongs to nested elements --
// e.g. for <th>Detail Code<span>*</span></th> this returns "Detail Code",
// not "Detail Code*" (the "*" is picked up separately when the span itself
// is visited in extractTextInRect's traversal).
function ownText(el) {
  let text = "";
  for (const node of el.childNodes) {
    if (node.nodeType === Node.TEXT_NODE) text += node.textContent;
  }
  return text.trim();
}

function extractTextInRect(containerEl, rect) {
  if (!containerEl) return "";
  const all = containerEl.querySelectorAll("*");
  const matches = [];
  for (const el of all) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const intersects = r.left < rect.right && r.right > rect.left && r.top < rect.bottom && r.bottom > rect.top;
    if (!intersects) continue;

    // Icon-only controls have no text nodes at all -- their meaning lives in
    // aria-label/title/alt instead, so always pull that in.
    const label = (el.getAttribute("aria-label") || el.getAttribute("title") || el.getAttribute("alt") || "").trim();
    if (label) matches.push(label);

    // Each matching element contributes only its OWN direct text -- nested
    // elements (e.g. a required-field "*" marker) are visited separately in
    // this same traversal, so using full textContent here would either lose
    // the parent's inline text (when a sibling text node sits next to a
    // matched child, as with the "*" markers above) or duplicate descendant
    // text at every ancestor level.
    const txt = ownText(el);
    if (txt) matches.push(txt);
  }
  return [...new Set(matches)].join("\n").slice(0, 4000);
}

// Page headings/labels (grid column headers, field labels) are rendered
// bold via CSS font-weight rather than a <b>/<strong> tag, so we can't just
// mirror the DOM -- instead we collect the text of everything bold on the
// page once per explain, and re-bold those same words wherever they show up
// inside the answer text.
const BOLD_FONT_WEIGHT = 600;

function collectBoldTerms(containerEl) {
  const seen = new Set();
  const terms = [];
  for (const el of containerEl.querySelectorAll("*")) {
    const weight = parseInt(window.getComputedStyle(el).fontWeight, 10);
    if (Number.isNaN(weight) || weight < BOLD_FONT_WEIGHT) continue;
    const text = ownText(el);
    if (text.length < 2 || !/[a-zA-Z]/.test(text)) continue;
    const key = text.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    terms.push(text);
  }
  return terms.sort((a, b) => b.length - a.length);
}

// Renders `text` as plain strings interleaved with <strong> for any
// substring that exactly matches one of the page's bold terms (longest
// terms win at a given position, so "Detail Code Description" is matched
// whole rather than as "Detail Code" + "Description").
function boldenKnownTerms(text, terms) {
  if (!text || terms.length === 0) return text;
  const escaped = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");
  return text.split(pattern).map((part, i) => (i % 2 === 1 ? <strong key={i}>{part}</strong> : part));
}

/**
 * Snipping-Tool-style Deep Dive explainer: click "Deep Dive" to arm select
 * mode (cursor becomes a crosshair), then a single plain click+drag over any
 * part of `containerRef`'s content draws a selection rectangle; releasing
 * fires a grounded explanation for whatever text was under it and disarms.
 * When not armed, normal clicks/scrolling are completely untouched.
 *
 * The result panel stays anchored near the selected area and auto-shifts
 * itself upward if its content grows past the bottom of the viewport.
 * `context` (optional) tells the backend what's currently on screen -- e.g.
 * { banner_id: "D00010001" } when TSADETL has that student loaded -- so a
 * vague follow-up like "what's my balance" resolves against the right
 * account even when the ID isn't typed or selected in the text itself.
 */
export default function BarDeepDiveOverlay({ containerRef, context, onDownloadReport, reportTriggerRef }) {
  const [armed, setArmed] = useState(false);
  const [rect, setRect] = useState(null);
  const [panel, setPanel] = useState(null); // { width, loading, explanation, sections, followUpQuestions, error }
  const [panelPos, setPanelPos] = useState(null); // { left, top }
  const [followups, setFollowups] = useState([]); // [{ question, loading, answer, error }] -- chat thread, kept in memory only
  const [customQuestion, setCustomQuestion] = useState("");

  const armedRef = useRef(false);
  const draggingRef = useRef(false);
  const startRef = useRef(null);
  const followupAnswerRef = useRef(null);
  const panelRef = useRef(null);
  const panelDragRef = useRef(null);
  const boldTermsRef = useRef([]);

  useEffect(() => {
    armedRef.current = armed;
    const container = containerRef.current;
    if (container) container.style.cursor = armed ? "crosshair" : "";
  }, [armed, containerRef]);

  useEffect(() => {
    const last = followups[followups.length - 1];
    if (last && !last.loading) {
      followupAnswerRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [followups]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === "Escape" && armedRef.current) setArmed(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Keep the panel fully on-screen vertically as its content grows (loading
  // -> explanation -> follow-up chips -> answer) -- pull it up if it now runs
  // past the bottom of the viewport, instead of leaving part of it unreachable.
  useEffect(() => {
    if (!panel || !panelPos || !panelRef.current) return;
    const height = panelRef.current.getBoundingClientRect().height;
    const maxTop = Math.max(VIEWPORT_MARGIN, window.innerHeight - height - VIEWPORT_MARGIN);
    if (panelPos.top > maxTop) {
      setPanelPos((p) => (p ? { ...p, top: maxTop } : p));
    }
  }, [panel, panelPos, followups]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onMouseDown = (e) => {
      if (e.button !== 0 || !armedRef.current) return;
      e.preventDefault();
      draggingRef.current = true;
      startRef.current = { x: e.clientX, y: e.clientY };
      setPanel(null);
      setPanelPos(null);
      setFollowups([]);
      setCustomQuestion("");
      setRect(stripFromDrag(startRef.current, startRef.current));
    };

    const onMouseMove = (e) => {
      if (!draggingRef.current || !startRef.current) return;
      setRect(stripFromDrag(startRef.current, { x: e.clientX, y: e.clientY }));
    };

    const onMouseUp = async (e) => {
      if (!draggingRef.current || !startRef.current) return;
      draggingRef.current = false;
      const finalRect = stripFromDrag(startRef.current, { x: e.clientX, y: e.clientY });
      startRef.current = null;
      setArmed(false); // one-shot, like Snipping Tool

      const width = finalRect.right - finalRect.left;
      const height = finalRect.bottom - finalRect.top;
      if (width < MIN_RECT_PX || height < MIN_RECT_PX) {
        setRect(null);
        return;
      }

      // Compact, fixed-width chat widget anchored near the drag selection,
      // rather than spanning the page's full content width.
      const panelWidth = Math.min(CHAT_PANEL_WIDTH, window.innerWidth - VIEWPORT_MARGIN * 2);
      setPanelPos({
        left: Math.max(VIEWPORT_MARGIN, Math.min(finalRect.left, window.innerWidth - panelWidth - VIEWPORT_MARGIN)),
        top: finalRect.bottom + 8,
      });

      // Download Report only makes sense when the selection was actually
      // over the ID field -- selecting elsewhere on the page (grid rows,
      // balance, etc.) still explains normally but won't offer the report.
      const triggerEl = reportTriggerRef?.current;
      const showDownloadReport = !!(triggerEl && rectsIntersect(finalRect, triggerEl.getBoundingClientRect()));

      boldTermsRef.current = collectBoldTerms(container);
      const text = extractTextInRect(container, finalRect);
      if (!text) {
        setPanel({
          width: panelWidth,
          loading: false,
          explanation: "",
          sections: [],
          images: [],
          followUpQuestions: [],
          debug: null,
          showDownloadReport,
          error: "Nothing selectable was found in that area -- try dragging over some text, a field, or a grid row.",
        });
        return;
      }

      setPanel({ width: panelWidth, loading: true, explanation: "", sections: [], images: [], followUpQuestions: [], debug: null, showDownloadReport, error: null });

      try {
        const { data } = await api.post("/help/explain", { text, context });
        setPanel({
          width: panelWidth,
          loading: false,
          explanation: data.explanation,
          sections: data.sections || [],
          images: data.images || [],
          followUpQuestions: data.follow_up_questions || [],
          debug: data.debug || null,
          showDownloadReport,
          error: null,
        });
      } catch (err) {
        const message = err?.response?.data?.error || "Couldn't get an explanation right now.";
        setPanel({ width: panelWidth, loading: false, explanation: "", sections: [], images: [], followUpQuestions: [], debug: null, showDownloadReport, error: message });
      }
    };

    container.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      container.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [containerRef]);

  const handleFollowupClick = async (question) => {
    let turnIndex;
    setFollowups((prev) => {
      turnIndex = prev.length;
      return [...prev, { question, loading: true, answer: "", images: [], debug: null, error: null }];
    });
    try {
      const { data } = await api.post("/help/followup", { question, context });
      setFollowups((prev) =>
        prev.map((f, i) =>
          i === turnIndex ? { ...f, loading: false, answer: data.answer, images: data.images || [], debug: data.debug || null } : f
        )
      );
    } catch (err) {
      const message = err?.response?.data?.error || "Couldn't get an answer right now.";
      setFollowups((prev) => prev.map((f, i) => (i === turnIndex ? { ...f, loading: false, error: message } : f)));
    }
  };

  const followupLoading = followups.some((f) => f.loading);

  const handleCustomQuestionSubmit = (e) => {
    e.preventDefault();
    const question = customQuestion.trim();
    if (!question || followupLoading) return;
    setCustomQuestion("");
    handleFollowupClick(question);
  };

  // Drag-to-move: mousedown on the panel header repositions the whole panel
  // as the mouse moves, independent of the selection rect / page scroll --
  // it only ever touches panelPos, never `rect` or window scroll position.
  const handlePanelHeaderMouseDown = (e) => {
    if (e.button !== 0 || !panelPos) return;
    e.preventDefault();
    panelDragRef.current = { startX: e.clientX, startY: e.clientY, origLeft: panelPos.left, origTop: panelPos.top };

    const onMove = (ev) => {
      const drag = panelDragRef.current;
      if (!drag) return;
      const bounds = panelRef.current?.getBoundingClientRect();
      const w = bounds?.width || panel?.width || CHAT_PANEL_WIDTH;
      const h = bounds?.height || 0;
      const left = Math.min(Math.max(drag.origLeft + (ev.clientX - drag.startX), -w + 60), window.innerWidth - 60);
      const top = Math.min(Math.max(drag.origTop + (ev.clientY - drag.startY), 0), Math.max(0, window.innerHeight - Math.min(h, 40)));
      setPanelPos({ left, top });
    };
    const onUp = () => {
      panelDragRef.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const closePanel = () => {
    setPanel(null);
    setPanelPos(null);
    setRect(null);
    setFollowups([]);
    setCustomQuestion("");
  };

  return (
    <>
      <button
        type="button"
        className={`bar-toggle-btn${armed ? " bar-toggle-btn--active" : ""}`}
        onClick={() => setArmed((a) => !a)}
        title={armed ? "Drag to select an area to explain (Esc to cancel)" : "Select an area for a deep dive"}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M9 3H5a2 2 0 0 0-2 2v4M15 3h4a2 2 0 0 1 2 2v4M9 21H5a2 2 0 0 1-2-2v-4M15 21h4a2 2 0 0 0 2-2v-4" />
        </svg>
        {armed ? "Selecting…" : "Deep Dive"}
      </button>
      {rect && (
        <div
          className="bar-select-rect"
          style={{
            // rect is tracked in viewport coordinates (from mouse clientX/Y);
            // converting to document coordinates here is what lets the box
            // stay absolute-positioned over the same content on scroll.
            left: rect.left + window.scrollX,
            top: rect.top + window.scrollY,
            width: rect.right - rect.left,
            height: rect.bottom - rect.top,
          }}
        />
      )}
      {panel && panelPos && (
        <div
          ref={panelRef}
          className="bar-explain-panel"
          style={{ left: panelPos.left, top: panelPos.top, width: panel.width }}
        >
          <div className="bar-explain-panel-head" onMouseDown={handlePanelHeaderMouseDown}>
            <span className="bar-explain-panel-title">Deep Dive</span>
            <button className="bar-explain-panel-close" onMouseDown={(e) => e.stopPropagation()} onClick={closePanel}>×</button>
          </div>
          <div className="bar-explain-panel-body">
            <div className="bar-chat-scroll">
              {panel.loading ? (
                <div className="bar-explain-loading"><div className="bar-spinner-md bar-spin--purple" /><span>Explaining…</span></div>
              ) : panel.error ? (
                <span className="bar-explain-error">{panel.error}</span>
              ) : (
                <>
                  <div className="bar-chat-answer bar-chat-answer--first">
                    <p>{boldenKnownTerms(panel.explanation, boldTermsRef.current)}</p>
                  </div>
                  <ReferenceImages images={panel.images} />
                  <div className="bar-log-actions-row">
                    <DebugLogLink debug={panel.debug} />
                    {onDownloadReport && panel.showDownloadReport && (
                      <button
                        type="button"
                        className="bar-download-report-btn"
                        onClick={onDownloadReport}
                        title="Download this student's transactions as an Excel report"
                      >
                        ⬇ Download Report
                      </button>
                    )}
                  </div>
                  {panel.followUpQuestions.length > 0 && (
                    <div className="bar-followup-row">
                      {panel.followUpQuestions.map((q, i) => (
                        <button
                          key={i}
                          type="button"
                          className={`bar-followup-chip${followups.some((f) => f.question === q) ? " bar-followup-chip--active" : ""}`}
                          onClick={() => handleFollowupClick(q)}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                  {followups.map((f, i) => (
                    <div
                      className="bar-chat-turn"
                      key={i}
                      ref={i === followups.length - 1 ? followupAnswerRef : null}
                    >
                      <div className="bar-chat-question">{f.question}</div>
                      <div className="bar-chat-answer">
                        {f.loading ? (
                          <div className="bar-explain-loading"><div className="bar-spinner-md bar-spin--purple" /><span>Thinking…</span></div>
                        ) : f.error ? (
                          <span className="bar-explain-error">{f.error}</span>
                        ) : (
                          <>
                            <p>{boldenKnownTerms(f.answer, boldTermsRef.current)}</p>
                            <ReferenceImages images={f.images} />
                            <DebugLogLink debug={f.debug} />
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
            {!panel.loading && !panel.error && (
              <form className="bar-ask-row" onSubmit={handleCustomQuestionSubmit}>
                <input
                  type="text"
                  className="bar-ask-input"
                  placeholder="Ask your own question about this…"
                  value={customQuestion}
                  onChange={(e) => setCustomQuestion(e.target.value)}
                />
                <button
                  type="submit"
                  className="bar-ask-send"
                  disabled={!customQuestion.trim() || followupLoading}
                >
                  Send
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}

// Reference-only screenshots from the technical design doc, surfaced when a
// retrieved chunk carries one -- these are never sent to the LLM, just linked
// here so the user can see the source page the answer is grounded in.
function ReferenceImages({ images }) {
  if (!images || images.length === 0) return null;
  return (
    <div className="bar-reference-images">
      {images.map((img) => (
        <a key={img} href={`${API_ORIGIN}/docs/${img}`} target="_blank" rel="noreferrer">
          <img src={`${API_ORIGIN}/docs/${img}`} alt={img} className="bar-reference-image" />
        </a>
      ))}
    </div>
  );
}

// Expandable "View backend log" link -- shows exactly what the backend did to
// produce this answer: which category/detail-code/student/term entities it
// detected in the text, the literal SQL (real values, not placeholders) it
// fired against SQLite for any of those, and which knowledge-base chunks
// (curated help rows + design-doc sections) were retrieved and their scores.
function DebugLogLink({ debug }) {
  const [open, setOpen] = useState(false);
  if (!debug) return null;

  const hasEntities = Object.values(debug.entities_detected || {}).some((v) => v.length > 0);

  return (
    <div className="bar-debug">
      <button type="button" className="bar-debug-toggle" onClick={() => setOpen((o) => !o)}>
        {open ? "▾" : "▸"} View backend log
      </button>
      {open && (
        <div className="bar-debug-body">
          <div className="bar-debug-section-title">Entities detected in this request</div>
          {hasEntities ? (
            <pre className="bar-debug-pre">{JSON.stringify(debug.entities_detected, null, 2)}</pre>
          ) : (
            <p className="bar-debug-empty">None -- no live SQL ran for this one, answer came from the static knowledge base only.</p>
          )}

          {debug.sql_queries?.length > 0 && (
            <>
              <div className="bar-debug-section-title">SQL fired against SQLite</div>
              {debug.sql_queries.map((q, i) => (
                <pre key={i} className="bar-debug-pre">{q}</pre>
              ))}
            </>
          )}

          <div className="bar-debug-section-title">Knowledge-base chunks retrieved</div>
          <pre className="bar-debug-pre">
            {(debug.kb_chunks_retrieved || [])
              .map((c) => `[${c.source}] ${c.heading}  (score ${c.score})`)
              .join("\n")}
          </pre>
        </div>
      )}
    </div>
  );
}
