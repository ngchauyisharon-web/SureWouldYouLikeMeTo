import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Archives } from "./Archives";
import { Help } from "./Help";
import { Landing } from "./Landing";
import { Play } from "./Play";
import { Settings } from "./Settings";
import { TopicSelect } from "./TopicSelect";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/topics" element={<TopicSelect />} />
        <Route path="/play/:slug" element={<Play />} />
        <Route path="/archives" element={<Archives />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/help" element={<Help />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
