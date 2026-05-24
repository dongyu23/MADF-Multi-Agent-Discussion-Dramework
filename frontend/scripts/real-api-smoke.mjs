const BACKEND_URL = process.env.MADF_BACKEND_URL ?? "http://localhost:8000";
const FRONTEND_URL = process.env.MADF_FRONTEND_URL ?? "http://localhost";
const USERNAME = process.env.MADF_SMOKE_USERNAME ?? "admin";
const PASSWORD = process.env.MADF_SMOKE_PASSWORD ?? "552323";

async function requestJson(label, url, init) {
  let response;

  try {
    response = await fetch(url, init);
  } catch (error) {
    throw new Error(`${label} 不可达：${error instanceof Error ? error.message : String(error)}`);
  }

  const text = await response.text();
  let body;

  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }

  if (!response.ok) {
    throw new Error(`${label} 返回 HTTP ${response.status}：${text.slice(0, 300)}`);
  }

  return body;
}

function assertSuccessPayload(label, payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error(`${label} 返回不是 JSON 对象`);
  }

  if (payload.code !== 200 && payload.code !== 0) {
    throw new Error(`${label} 业务状态异常：${JSON.stringify(payload).slice(0, 300)}`);
  }
}

function assertToken(label, payload) {
  assertSuccessPayload(label, payload);

  const token = payload.data?.token?.token ?? payload.data?.token;
  if (typeof token !== "string" || token.length < 20) {
    throw new Error(`${label} 未返回有效 token：${JSON.stringify(payload).slice(0, 300)}`);
  }
}

async function login(label, baseUrl) {
  return requestJson(label, `${baseUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: USERNAME, password: PASSWORD }),
  });
}

async function main() {
  const health = await requestJson("主后端 health", `${BACKEND_URL}/api/v1/health`);
  assertSuccessPayload("主后端 health", health);

  const backendLogin = await login("主后端真实登录", BACKEND_URL);
  assertToken("主后端真实登录", backendLogin);

  const proxiedLogin = await login("前端入口代理登录", FRONTEND_URL);
  assertToken("前端入口代理登录", proxiedLogin);

  console.log("real-api-smoke passed");
  console.log(`backend: ${BACKEND_URL}`);
  console.log(`frontend entry proxy: ${FRONTEND_URL}/api`);
  console.log(`user: ${USERNAME}`);
}

main().catch((error) => {
  console.error("real-api-smoke failed");
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
