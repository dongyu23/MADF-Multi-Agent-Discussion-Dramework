<template>
  <a-config-provider 
    :locale="zhCN" 
    :theme="{ 
      algorithm: theme.darkAlgorithm,
      token: {
        colorPrimary: '#D4AF37',
        colorBgBase: '#0B0B0C',
        colorBgContainer: '#15151A',
        colorTextBase: '#F2E8CF',
        fontFamily: '\'Azeret Mono\', monospace',
        fontFamilyCode: '\'Azeret Mono\', monospace',
        borderRadius: 2,
        colorBorder: '#333333',
      },
      components: {
        Card: {
          colorBgContainer: 'rgba(21, 21, 26, 0.8)',
          headerFontSize: 24,
        },
        Button: {
          borderRadius: 0,
          fontWeight: 600,
        }
      }
    }"
  >
    <div class="app-container noise-bg">
      <router-view />
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { theme } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { useConfigStore } from '@/stores/config'

const configStore = useConfigStore()
</script>

<style>
/* Global reset and aesthetic */
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  background-color: #0B0B0C;
  color: #F2E8CF;
}

.app-container {
  height: 100%;
  overflow: auto;
  position: relative;
}

/* Noise overlay for that gritty, archival texture */
.noise-bg::before {
  content: "";
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.04;
  background: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
}

h1, h2, h3, h4, h5, h6, .ant-card-head-title, .ant-typography {
  font-family: 'Cormorant Garamond', serif !important;
  letter-spacing: 0.02em;
}

.ant-btn {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-family: 'Azeret Mono', monospace;
}

/* Subtle glowing line at top of cards to look like a terminal interface */
.ant-card {
  border-top: 2px solid #D4AF37 !important;
  backdrop-filter: blur(10px);
}
</style>
