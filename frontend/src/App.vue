<template>
  <a-config-provider 
    :locale="zhCN" 
    :theme="{ 
      algorithm: theme.darkAlgorithm,
      token: {
        colorPrimary: '#1890ff',
        colorBgBase: '#0d0d12',
        colorBgContainer: '#191923',
        colorTextBase: '#ffffff',
        fontFamily: '-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, \'Helvetica Neue\', Arial, \'Noto Sans\', sans-serif',
        borderRadius: 8,
        colorBorder: 'rgba(255, 255, 255, 0.1)',
      },
      components: {
        Card: {
          colorBgContainer: 'rgba(25, 25, 35, 0.6)',
          headerFontSize: 16,
        },
        Button: {
          borderRadius: 8,
          fontWeight: 500,
        }
      }
    }"
  >
    <div class="app-container">
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
/* Global reset and refined aesthetic */
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  background-color: #0d0d12;
  color: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-container {
  height: 100%;
  overflow: auto;
  position: relative;
}

/* Subtle background pattern */
.app-container::before {
  content: "";
  position: fixed;
  top: 0; left: 0; width: 100vw; height: 100vh;
  pointer-events: none;
  z-index: -1;
  background-image: radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 24px 24px;
}

/* Smooth transitions for links and buttons */
a {
  transition: all 0.3s ease;
}

/* Elegant scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
