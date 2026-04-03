<template>
  <a-config-provider 
    :locale="zhCN" 
    :theme="{ 
      algorithm: theme.darkAlgorithm,
      token: {
        colorPrimary: '#1677ff',
        colorBgBase: '#141414',
        colorBgContainer: '#1f1f1f',
        colorTextBase: 'rgba(255, 255, 255, 0.85)',
        fontFamily: '-apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, \'Helvetica Neue\', Arial, \'Noto Sans\', sans-serif',
        borderRadius: 6,
        colorBorder: '#424242',
      },
      components: {
        Card: {
          colorBgContainer: '#1f1f1f',
          headerFontSize: 16,
        },
        Button: {
          borderRadius: 6,
        },
        Layout: {
          colorBgHeader: '#141414',
          colorBgBody: '#141414',
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

// We are forcing dark mode here for a consistent AI tool feel.
const configStore = useConfigStore()
</script>

<style>
/* Global reset and refined aesthetic */
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
  background-color: #141414;
  color: rgba(255, 255, 255, 0.85);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-container {
  height: 100%;
  position: relative;
}

/* Smooth transitions for links and buttons */
a {
  transition: all 0.3s ease;
}

/* Standard scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
