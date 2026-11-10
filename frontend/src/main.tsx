import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import App from "./App";
import SlatePage from "./pages/SlatePage";
import MatchPage from "./pages/MatchPage";
import PerformancePage from "./pages/PerformancePage";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

// react-router v7 data router (createBrowserRouter + RouterProvider). The
// declarative <BrowserRouter><Routes> form failed to re-render on client-side
// navigation with React 19.2; this is the supported v7 pattern.
const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <SlatePage competition="epl" /> },
      { path: "world-cup", element: <SlatePage competition="wc" /> },
      { path: "record", element: <PerformancePage /> },
      { path: "match/:matchId", element: <MatchPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
