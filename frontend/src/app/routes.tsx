import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";

export const router = createBrowserRouter([
  {
    path: "/",
    lazy: () => import("./pages/Home").then(m => ({ Component: m.Home })),
  },
  {
    path: "/login",
    lazy: () => import("./pages/Login").then(m => ({ Component: m.Login })),
  },
  {
    path: "/register",
    lazy: () => import("./pages/Login").then(m => ({ Component: m.Register })),
  },
  {
    path: "/",
    Component: Layout,
    children: [
      { path: "dashboard", lazy: () => import("./pages/Dashboard").then(m => ({ Component: m.Dashboard })) },
      { path: "gallery", lazy: () => import("./pages/Gallery").then(m => ({ Component: m.Gallery })) },
      { path: "gallery/:id/view", lazy: () => import("./pages/Editor").then(m => ({ Component: m.Editor })) },
      { path: "characters", lazy: () => import("./pages/Characters").then(m => ({ Component: m.Characters })) },
      { path: "characters/generate", lazy: () => import("./pages/GenerateSkill").then(m => ({ Component: m.GenerateSkill })) },
      { path: "characters/:id", lazy: () => import("./pages/Editor").then(m => ({ Component: m.Editor })) },
      { path: "discussions", lazy: () => import("./pages/Discussions").then(m => ({ Component: m.Discussions })) },
      { path: "discussions/new", lazy: () => import("./pages/NewDiscussion").then(m => ({ Component: m.NewDiscussion })) },
      { path: "discussions/:id", lazy: () => import("./pages/DiscussionRoom").then(m => ({ Component: m.DiscussionRoom })) },
    ],
  },
]);
