import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const outputDir = path.resolve(currentDir, "../../../output/playwright");
fs.mkdirSync(outputDir, { recursive: true });
const adminUser = process.env.MADF_E2E_USER || "admin";
const adminPassword = process.env.MADF_E2E_PASSWORD || "552323";
const e2eToken = "e2e-token";

async function mockMainApi(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const pathName = url.pathname;

    if (pathName === "/api/v1/auth/login") {
      const body = request.postDataJSON() as { username?: string; password?: string };
      expect(body.username).toBe(adminUser);
      expect(body.password).toBe(adminPassword);
      await route.fulfill({
        status: 200,
        json: {
          code: 0,
          message: "ok",
          data: {
            token: { token: e2eToken },
            user: { id: "admin-id", username: adminUser },
          },
        },
      });
      return;
    }

    if (pathName === "/api/v1/auth/me") {
      const authHeader = request.headers().authorization || "";
      if (authHeader === `Bearer ${e2eToken}`) {
        await route.fulfill({
          status: 200,
          json: { code: 0, message: "ok", data: { user: { id: "admin-id", username: adminUser } } },
        });
      } else {
        await route.fulfill({
          status: 401,
          json: { code: 1002, message: "认证失败", data: null },
        });
      }
      return;
    }

    if (pathName === "/api/v1/characters/gallery") {
      await route.fulfill({
        status: 200,
        json: {
          code: 0,
          message: "ok",
          data: {
            items: [
              { id: "gallery-1", owner_id: "public", name: "公共角色", description: "可复制的公开 Skill", tags: [], is_public: true, status: "ready", created_at: new Date().toISOString() },
            ],
          },
        },
      });
      return;
    }

    if (pathName === "/api/v1/characters") {
      await route.fulfill({
        status: 200,
        json: {
          code: 0,
          message: "ok",
          data: {
            total: 2,
            items: [
              { id: "char-1", owner_id: "admin-id", name: "战略家-perspective", description: "从长期主义出发拆解问题。", tags: [], is_public: false, status: "ready", created_at: new Date().toISOString() },
              { id: "char-2", owner_id: "admin-id", name: "工程师-perspective", description: "关注实现路径与约束。", tags: [], is_public: false, status: "ready", created_at: new Date().toISOString() },
            ],
          },
        },
      });
      return;
    }

    if (pathName === "/api/v1/discussions") {
      await route.fulfill({
        status: 200,
        json: {
          code: 0,
          message: "ok",
          data: {
            total: 1,
            items: [
              {
                id: "discussion-1",
                topic: "AI 圆桌如何帮助学生突破信息差？",
                status: "running",
                duration: 900,
                created_at: new Date().toISOString(),
                agents: [{ id: "char-1" }, { id: "char-2" }],
              },
            ],
          },
        },
      });
      return;
    }

    await route.fulfill({ status: 404, json: { code: 404, message: `Unhandled E2E route: ${pathName}`, data: null } });
  });
}

async function expectNoHorizontalOverflow(page: import("@playwright/test").Page) {
  const size = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(size.scrollWidth, `${size.scrollWidth}/${size.clientWidth}`).toBeLessThanOrEqual(size.clientWidth + 1);
}

test.beforeEach(async ({ page }) => {
  await mockMainApi(page);
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
});

test("public landing page is the default route on desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: /让多个 AI 角色围坐下来/ })).toBeVisible();
  await expect(page.getByText("框架").first()).toBeVisible();
  await expect(page.getByText("流程").first()).toBeVisible();
  await expect(page.getByText("审计").first()).toBeVisible();
  await expect(page.getByText("进入系统").first()).toBeVisible();

  const scroll = await page.evaluate(() => ({
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight,
  }));
  expect(scroll.scrollHeight).toBeGreaterThan(scroll.clientHeight * 2);
  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: path.join(outputDir, "madf-home-desktop.png"), fullPage: true });
});

test("public landing page is responsive on tablet and mobile", async ({ page }) => {
  for (const viewport of [
    { name: "tablet", width: 768, height: 1024 },
    { name: "mobile", width: 390, height: 900 },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /让多个 AI 角色围坐下来/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /进入系统/ })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.screenshot({ path: path.join(outputDir, `madf-home-${viewport.name}.png`), fullPage: true });
  }
});

test("login and register pages can return to landing page", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "欢迎回来" })).toBeVisible();
  await page.getByRole("link", { name: "返回首页" }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.goto("/register");
  await expect(page.getByRole("heading", { name: "创建账号" })).toBeVisible();
  await page.getByRole("link", { name: "返回首页" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.screenshot({ path: path.join(outputDir, "madf-register-return-home.png"), fullPage: true });
});

test("dashboard is protected and valid login reaches the app dashboard", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?redirect=%2Fdashboard$/);

  await page.getByPlaceholder("输入用户名").fill(adminUser);
  await page.getByPlaceholder("输入密码（至少6位）").fill(adminPassword);
  await page.getByRole("button", { name: /登录/ }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("角色圆桌")).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: path.join(outputDir, "madf-dashboard-after-login.png"), fullPage: false });

  await page.getByRole("link", { name: "展示首页" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: /让多个 AI 角色围坐下来/ })).toBeVisible();
});

test("invalid token is cleared and redirected away from dashboard", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("token", "invalid-token-for-e2e"));
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?redirect=%2Fdashboard$/);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("token"))).toBeNull();
});
