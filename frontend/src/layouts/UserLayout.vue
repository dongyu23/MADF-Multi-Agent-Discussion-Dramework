<template>
  <div class="user-layout-container">
    <div class="user-layout-content">
      <div class="top-header">
        <div class="header-logo">
          <span class="title">MADF 论坛枢纽</span>
        </div>
        <div class="header-desc">
          多智能体圆桌讨论框架
        </div>
      </div>

      <div class="main-content">
        <router-view />
      </div>

      <div class="user-layout-footer">
        <div class="links">
          <a href="#">帮助文档</a>
          <a href="#">隐私协议</a>
          <a href="#">服务条款</a>
        </div>
        <div class="copyright">
          Copyright &copy; 2026 Trae AI
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-layout-container {
  width: 100%;
  min-height: 100vh;
  background-color: #141414;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: auto;
}

.user-layout-content {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 400px;
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.top-header {
  text-align: center;
  margin-bottom: 40px;
}

.header-logo .title {
  font-size: 28px;
  color: rgba(255, 255, 255, 0.85);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-weight: 600;
  letter-spacing: 1px;
}

.header-desc {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.45);
  margin-top: 12px;
}

.main-content {
  width: 100%;
  margin-bottom: 40px;
}

.user-layout-footer {
  width: 100%;
  text-align: center;
}

.user-layout-footer .links {
  margin-bottom: 12px;
  font-size: 14px;
}

.user-layout-footer .links a {
  color: rgba(255, 255, 255, 0.45);
  transition: all 0.3s;
  text-decoration: none;
  margin: 0 12px;
}

.user-layout-footer .links a:hover {
  color: rgba(255, 255, 255, 0.85);
}

.user-layout-footer .copyright {
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
}

@media (max-width: 576px) {
  .user-layout-content {
    width: 100%;
    padding: 24px 16px;
  }
}
</style>
