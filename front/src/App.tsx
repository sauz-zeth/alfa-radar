import { QueryClientProvider } from "@tanstack/react-query";
import { ApiProvider, createQueryClient } from "./api";
import { AuthProvider } from "./auth/AuthProvider";
import { LoginPage } from "./auth/LoginPage";
import { RegisterPage } from "./auth/RegisterPage";
import { Splash } from "./auth/Splash";
import { useAuth } from "./auth/useAuth";
import { OnboardingGate } from "./onboarding/OnboardingGate";
import { Redirect, RouterProvider, useRouter } from "./router";
import "./index.css";

const queryClient = createQueryClient();

function AppRoutes() {
  const { status } = useAuth();
  const { path } = useRouter();

  if (status === "loading") return <Splash />;

  if (status === "anonymous") {
    return path === "/register" ? <RegisterPage /> : <LoginPage />;
  }

  if (path === "/login" || path === "/register") return <Redirect to="/" />;

  return <OnboardingGate />;
}

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
        <AuthProvider>
          <RouterProvider>
            <AppRoutes />
          </RouterProvider>
        </AuthProvider>
      </ApiProvider>
    </QueryClientProvider>
  );
}

export default App;
