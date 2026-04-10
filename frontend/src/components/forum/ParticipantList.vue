<template>
  <div class="participant-grid">
    <div v-for="item in participants" :key="item.persona.id" class="participant-card">
      <div class="card-header">
        <a-avatar :style="{ backgroundColor: getAvatarColor(item.persona.name) }" size="large">
          {{ item.persona.name[0] }}
        </a-avatar>
        <div class="header-info">
          <div class="name-row">
            <span class="participant-name">{{ item.persona.name }}</span>
            <a-tooltip v-if="item.persona.title" :title="item.persona.title">
                <a-tag color="blue" size="small" class="title-tag">{{ item.persona.title }}</a-tag>
            </a-tooltip>
            <a-tag 
              v-if="store.agentStates?.[item.persona.name]?.temporal?.current_emotion" 
              color="orange" 
              size="small"
              class="title-tag"
            >
              {{ store.agentStates[item.persona.name].temporal.current_emotion }}
            </a-tag>
          </div>
          <a-tooltip v-if="item.persona.stance" :title="item.persona.stance">
            <a-tag :color="getStanceColor(item.persona.stance)" size="small" class="stance-tag">
                {{ item.persona.stance }}
            </a-tag>
          </a-tooltip>
        </div>
      </div>
      <div class="card-body">
        <p class="bio-text">{{ item.persona.bio || '暂无简介' }}</p>
        
        <!-- 新增：内部状态探针 -->
        <div v-if="store.agentStates?.[item.persona.name]" style="margin-top: 12px;">
          <a-popover title="Agent 内部状态 (Internal States)" trigger="hover" placement="right">
            <template #content>
              <div style="max-width: 300px; font-size: 12px;">
                <div v-if="store.agentStates[item.persona.name].beliefs?.length" style="margin-bottom: 8px;">
                  <strong>核心信念:</strong>
                  <ul style="padding-left: 16px; margin: 4px 0 0 0;">
                    <li v-for="(belief, idx) in store.agentStates[item.persona.name].beliefs" :key="idx" style="margin-bottom: 4px;">
                      {{ belief.statement }} (置信度: {{ belief.confidence }})
                    </li>
                  </ul>
                </div>
                <div v-if="store.agentStates[item.persona.name].relations?.length" style="margin-bottom: 8px;">
                  <strong>人际认知:</strong>
                  <ul style="padding-left: 16px; margin: 4px 0 0 0;">
                    <li v-for="(rel, idx) in store.agentStates[item.persona.name].relations" :key="idx" style="margin-bottom: 4px;">
                      对 {{ rel.target_name }} : {{ rel.attitude }} (信任: {{ rel.trust }}, 敌意: {{ rel.hostility }})
                    </li>
                  </ul>
                </div>
                <div v-if="store.agentStates[item.persona.name].behavior_patterns?.length">
                  <strong>行为模式:</strong>
                  <ul style="padding-left: 16px; margin: 4px 0 0 0;">
                    <li v-for="(bp, idx) in store.agentStates[item.persona.name].behavior_patterns" :key="idx" style="margin-bottom: 4px;">
                      {{ bp.pattern }} (置信度: {{ bp.confidence }})
                    </li>
                  </ul>
                </div>
              </div>
            </template>
            <a-button size="small" type="dashed" block>
              <ReadOutlined /> 窥探内心
            </a-button>
          </a-popover>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ReadOutlined } from '@ant-design/icons-vue'
import { useForumStore } from '@/stores/forum'

const store = useForumStore()
const participants = computed(() => store.currentForum?.participants ?? [])

const getAvatarColor = (name: string) => {
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const getStanceColor = (stance: string) => {
  if (stance.includes('支持') || stance.includes('正方')) return 'success'
  if (stance.includes('反对') || stance.includes('反方')) return 'error'
  return 'default'
}
</script>

<style scoped>
.participant-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  padding: 8px;
}

.participant-card {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #f0f0f0;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.participant-card:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
  overflow: hidden; /* Ensure flex child shrinks */
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.participant-name {
  font-weight: 600;
  font-size: 15px;
  color: #262626;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0; /* Keep name visible */
  max-width: 100%;
}

.title-tag, .stance-tag {
  align-self: flex-start;
  margin: 0;
  max-width: 100%;
  white-space: nowrap; /* Back to single line */
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  padding: 2px 8px;
  line-height: 1.4;
  text-align: left;
}

.bio-text {
  margin: 0;
  font-size: 13px;
  color: #595959;
  display: -webkit-box;
  -webkit-line-clamp: 6; /* Show more lines now that tags are compact */
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.6;
  max-height: 125px; /* Fixed height to prevent uneven cards */
}
</style>