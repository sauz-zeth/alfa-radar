import { PageOutlet } from "./components/PageOutlet";
import { Nav } from "./components/Nav";
import { RouterProvider } from "./router";
import "./index.css";

export function App() {
  return (
    <RouterProvider>
      <div className="app">
        <Nav />
        <PageOutlet />
      </div>
    </RouterProvider>
  );
}

export default App;
