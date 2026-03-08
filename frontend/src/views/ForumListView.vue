<template>
  <div class="forum-list-page">
    <div class="page-header">
      <div class="header-title">
        <span class="title">圆桌论坛</span>
        <span class="subtitle">创建多智能体讨论组，观察思维碰撞</span>
      </div>
      <a-button type="primary" size="large" @click="showModal()">
        <plus-outlined /> 发起新讨论
      </a-button>
    </div>

    <a-spin :spinning="forumStore.loading">
      <div class="forum-grid">
        <a-card
          v-for="item in forumStore.forums"
          :key="item.id"
          hoverable
          class="forum-card"
          @click="$router.push(`/forums/${item.id}`)"
        >
          <a-card-meta>
            <template #title>
              <div class="card-title">
                <span class="topic">{{ item.topic }}</span>
                <a-tag :color="getStatusColor(item.status)">{{ getStatusText(item.status) }}</a-tag>
              </div>
            </template>
            <template #description>
              <div class="card-desc">
                创建时间: {{ new Date(item.start_time).toLocaleString() }}
              </div>
            </template>
            <template #avatar>
              <a-avatar
                shape="square"
                size="large"
                :style="{ backgroundColor: getAvatarColor(item.topic) }"
              >
                {{ item.topic[0] }}
              </a-avatar>
            </template>
          </a-card-meta>
          
          <div class="card-footer">
            <a-space>
              <a-popconfirm title="确定删除该论坛吗？" @confirm.stop="handleDelete(item.id)">
                <a-button type="text" danger size="small"><delete-outlined /></a-button>
              </a-popconfirm>
              <span class="action-text">点击进入讨论 <arrow-right-outlined /></span>
            </a-space>
          </div>
        </a-card>
        
        <div v-if="forumStore.forums.length === 0" class="empty-state">
          <a-empty description="暂无正在进行的论坛，发起一个新的话题吧" />
        </div>
      </div>
    </a-spin>

    <a-modal
      v-model:open="visible"
      title="发起新讨论"
      @ok="handleOk"
      :confirmLoading="submitting"
      width="520px"
    >
      <a-form layout="vertical" ref="formRef" :model="formState">
        <a-form-item
          label="讨论主题"
          name="topic"
          :rules="[{ required: true, message: '请输入讨论主题' }]"
        >
          <a-input
            v-model:value="formState.topic"
            placeholder="例如：人工智能对未来就业的影响"
            size="large"
          />
        </a-form-item>
        
        <a-form-item label="主持人" name="moderator_id">
          <a-select
            v-model:value="formState.moderator_id"
            placeholder="选择主持人（默认：系统默认主持人）"
            :options="moderatorOptions"
            allow-clear
            size="large"
          >
          </a-select>
        </a-form-item>

        <a-form-item
          label="邀请参与者"
          name="participant_ids"
          :rules="[{ required: true, message: '请至少选择一位智能体' }]"
        >
          <a-select
            v-model:value="formState.participant_ids"
            mode="multiple"
            placeholder="选择参与讨论的智能体"
            :options="personaOptions"
            :loading="personaStore.loading"
            size="large"
            style="width: 100%"
          >
            <template #option="{ label }">
               <div style="display: flex; justify-content: space-between">
                 <span>{{ label }}</span>
               </div>
            </template>
          </a-select>
          <div style="margin-top: 8px; color: #8c8c8c; font-size: 12px;">
            提示：您可以选择自己创建的智能体，也可以邀请公开的智能体加入。
          </div>
        </a-form-item>
        
        <a-form-item label="论坛时长 (分钟)" name="duration">
            <a-input-number v-model:value="formState.duration" :min="5" :max="120" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { message } from 'ant-design-vue'
import { PlusOutlined, ArrowRightOutlined, DeleteOutlined } from '@ant-design/icons-vue'

const forumStore = useForumStore()
const personaStore = usePersonaStore()
const visible = ref(false)
const submitting = ref(false)

const formState = reactive({
  topic: '',
  participant_ids: [] as number[],
  moderator_id: undefined as number | undefined,
  duration: 30
})

onMounted(() => {
  forumStore.fetchForums()
  forumStore.fetchModerators()
  personaStore.fetchPersonas()
})

const moderatorOptions = computed(() => {
  return forumStore.moderators.map(m => ({
    label: m.name,
    value: m.id
  }))
})

const personaOptions = computed(() => {
  return personaStore.personas.map(p => ({
    label: p.name,
    value: p.id
  }))
})

const getStatusColor = (status: string) => {
  switch (status) {
    case 'running': return 'processing'
    case 'pending': return 'warning'
    case 'closed':
    case 'finished': return 'default'
    case 'active': return 'processing'
    default: return 'default'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'running': return '进行中'
    case 'pending': return '未开始'
    case 'closed':
    case 'finished': return '已结束'
    case 'active': return '进行中'
    default: return '未知'
  }
}

const getAvatarColor = (topic: string) => {
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < topic.length; i++) {
    hash = topic.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const showModal = async () => {
  await forumStore.fetchModerators()
  visible.value = true
  formState.topic = ''
  formState.participant_ids = []
  formState.moderator_id = undefined
  formState.duration = 30
}

const handleOk = async () => {
  if (!formState.topic || formState.participant_ids.length === 0) {
    message.warning('请填写完整信息')
    return
  }
  
  submitting.value = true
  try {
    await forumStore.fetchModerators()
    if (formState.moderator_id && !forumStore.moderators.some(m => m.id === formState.moderator_id)) {
      formState.moderator_id = undefined
      message.warning('所选主持人已失效，请重新选择')
      return
    }
    await forumStore.createForum(formState.topic, formState.participant_ids, formState.duration, formState.moderator_id)
    visible.value = false
  } catch (e: unknown) {
    if (e instanceof Error) {
        message.error(e.message || '创建失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
    await forumStore.deleteForum(id)
    await forumStore.fetchForums()
}
</script>

<style scoped>
.forum-list-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-title {
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 24px;
  font-weight: 500;
  color: rgba(0,0,0,0.85);
}

.subtitle {
  font-size: 14px;
  color: rgba(0,0,0,0.45);
  margin-top: 4px;
}

.forum-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.forum-card {
  border-radius: 8px;
  transition: all 0.3s;
  cursor: pointer;
}

.forum-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title .topic {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 8px;
}

.card-desc {
  margin-top: 8px;
  font-size: 12px;
}

.card-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  color: #1890ff;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 48px 0;
  text-align: center;
}
</style>
