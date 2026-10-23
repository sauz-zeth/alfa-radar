import { QueryClientProvider } from "@tanstack/react-query";
import { ApiProvider, createQueryClient } from "./api";
import { PageOutlet } from "./components/PageOutlet";
import { Nav } from "./components/Nav";
import { RouterProvider } from "./router";
import "./index.css";

const queryClient = createQueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ApiProvider
        config={{
          getToken: () =>
            typeof localStorage === "undefined"
              ? null
              : localStorage.getItem("token"),
        }}
      >
        <RouterProvider>
          <div className="app">
            <Nav />
            <PageOutlet />
          </div>
        </RouterProvider>
      </ApiProvider>
    </QueryClientProvider>
  );
}

export default App;
