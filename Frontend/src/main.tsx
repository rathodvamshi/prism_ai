import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
// Import theme store to initialize theme immediately
import "./stores/themeStore";

createRoot(document.getElementById("root")!).render(<App />);
