import { createBrowserRouter } from "react-router";
import { AuditLayout } from "./components/Layout";

export const router = createBrowserRouter([
  {
    path: "/login",
    lazy: () => import("./pages/AdminLogin").then((m) => ({ Component: m.AdminLogin })),
  },
  {
    path: "/",
    Component: AuditLayout,
    children: [
      {
        index: true,
        lazy: () => import("./pages/Dashboard").then((m) => ({ Component: m.Dashboard })),
      },
      {
        path: "users",
        lazy: () => import("./pages/UserManagement").then((m) => ({ Component: m.UserManagement })),
      },
      {
        path: "users/:id",
        lazy: () => import("./pages/UserDetail").then((m) => ({ Component: m.UserDetail })),
      },
      {
        path: "discussions",
        lazy: () => import("./pages/DiscussionMonitor").then((m) => ({ Component: m.DiscussionMonitor })),
      },
      {
        path: "discussions/:id",
        lazy: () => import("./pages/DiscussionDetail").then((m) => ({ Component: m.DiscussionDetail })),
      },
      {
        path: "audit",
        lazy: () => import("./pages/AuditTrail").then((m) => ({ Component: m.AuditTrail })),
      },
      {
        path: "audit/:id",
        lazy: () => import("./pages/AuditEventDetail").then((m) => ({ Component: m.AuditEventDetail })),
      },
      {
        path: "health",
        lazy: () => import("./pages/SystemHealth").then((m) => ({ Component: m.SystemHealth })),
      },
      {
        path: "admins",
        lazy: () => import("./pages/AdminManagement").then((m) => ({ Component: m.AdminManagement })),
      },
      {
        path: "settings",
        lazy: () => import("./pages/Settings").then((m) => ({ Component: m.Settings })),
      },
    ],
  },
], { basename: "/audit" });
