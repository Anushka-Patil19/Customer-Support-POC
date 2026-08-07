import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import HelpPOCHeader from "./components/HelpPOCHeader";
import TTVDCAT from "./pages/TTVDCAT";
import TSADETC from "./pages/TSADETC";
import TSADETL from "./pages/TSADETL";

export default function App() {
  return (
    <BrowserRouter>
      <HelpPOCHeader />
      <Routes>
        <Route path="/" element={<Navigate to="/ttvdcat" replace />} />
        <Route path="/ttvdcat" element={<TTVDCAT />} />
        <Route path="/tsadetc" element={<TSADETC />} />
        <Route path="/tsadetl" element={<TSADETL />} />
      </Routes>
    </BrowserRouter>
  );
}
