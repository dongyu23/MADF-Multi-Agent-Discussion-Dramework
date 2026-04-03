<template>
  <div class="split-layout-container">
    <div class="split-left">
      <div class="brand-content">
        <div class="logo">
          <div class="logo-mark">M</div>
          <span class="logo-text">MADF Platform</span>
        </div>
        <h1 class="brand-title">探索多智能体的<br/>无限可能</h1>
        <p class="brand-desc">
          一个专为 AI 协作与思想实验打造的圆桌讨论框架。<br/>
          在这里，您可以配置不同性格的虚拟智能体，观察他们在特定话题下的多维思想碰撞。
        </p>
        <div class="brand-illustration">
          <div class="network-nodes">
            <div class="node n1"></div>
            <div class="node n2"></div>
            <div class="node n3"></div>
            <div class="line l1"></div>
            <div class="line l2"></div>
            <div class="line l3"></div>
          </div>
        </div>
      </div>
      <div class="brand-footer">
        © 2026 Trae AI. All rights reserved.
      </div>
    </div>
    
    <div class="split-right">
      <div class="form-container">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </div>
  </div>
</template>

<style scoped>
.split-layout-container {
  display: flex;
  min-height: 100vh;
  width: 100%;
  background-color: #09090b;
}

.split-left {
  flex: 1;
  position: relative;
  background: linear-gradient(135deg, #1f1f2e 0%, #0d0d12 100%);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 64px;
  overflow: hidden;
}

.split-left::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 32px 32px;
  z-index: 1;
}

.brand-content {
  position: relative;
  z-index: 2;
  max-width: 500px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 64px;
}

.logo-mark {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #1677ff 0%, #36cfc9 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 800;
  font-size: 24px;
  box-shadow: 0 0 20px rgba(22, 119, 255, 0.4);
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.5px;
}

.brand-title {
  font-size: 48px;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.2;
  margin-bottom: 24px;
  letter-spacing: -1px;
}

.brand-desc {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.65);
  line-height: 1.6;
  margin-bottom: 48px;
}

/* Abstract Network Illustration */
.brand-illustration {
  position: relative;
  height: 200px;
  margin-top: 64px;
}

.network-nodes {
  position: relative;
  width: 100%;
  height: 100%;
}

.node {
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #1677ff;
  box-shadow: 0 0 15px rgba(22, 119, 255, 0.6);
  z-index: 2;
}

.n1 { top: 20%; left: 10%; animation: float1 4s ease-in-out infinite alternate; }
.n2 { top: 60%; left: 40%; background: #36cfc9; box-shadow: 0 0 15px rgba(54, 207, 201, 0.6); animation: float2 5s ease-in-out infinite alternate; }
.n3 { top: 30%; left: 80%; background: #722ed1; box-shadow: 0 0 15px rgba(114, 46, 209, 0.6); animation: float3 6s ease-in-out infinite alternate; }

.line {
  position: absolute;
  background: linear-gradient(90deg, rgba(22, 119, 255, 0.5), transparent);
  height: 2px;
  z-index: 1;
  transform-origin: left center;
}

.l1 { top: 24%; left: 12%; width: 150px; transform: rotate(35deg); }
.l2 { top: 64%; left: 42%; width: 180px; transform: rotate(-30deg); background: linear-gradient(90deg, rgba(54, 207, 201, 0.5), transparent); }
.l3 { top: 24%; left: 12%; width: 300px; transform: rotate(5deg); background: linear-gradient(90deg, rgba(22, 119, 255, 0.5), rgba(114, 46, 209, 0.2)); }

@keyframes float1 { from { transform: translateY(0); } to { transform: translateY(-20px); } }
@keyframes float2 { from { transform: translateY(0); } to { transform: translateY(15px); } }
@keyframes float3 { from { transform: translateY(0); } to { transform: translateY(-10px); } }

.brand-footer {
  position: relative;
  z-index: 2;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.35);
}

.split-right {
  width: 480px;
  background: #141414;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
  z-index: 10;
}

.form-container {
  width: 100%;
  max-width: 400px;
  padding: 40px;
}

/* Transition */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

@media (max-width: 1024px) {
  .split-left {
    display: none; /* Hide branding on smaller screens */
  }
  .split-right {
    width: 100%;
    box-shadow: none;
  }
}
</style>
