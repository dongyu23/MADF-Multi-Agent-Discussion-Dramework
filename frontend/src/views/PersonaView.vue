<template>
  <div class="persona-page">
    <div class="persona-content-wrapper">
        <div class="page-header">
          <div class="header-title">
            <span class="title">智能体工坊</span>
            <span class="subtitle">管理您的智能体角色，定义个性与认知体系</span>
          </div>
          <a-space>
            <a-button type="primary" ghost @click="showRealGodModal" class="real-god-btn">
              <global-outlined /> 上帝生成真实角色 (联网)
            </a-button>
            <a-button type="primary" @click="showModal()">
              <plus-outlined /> 创建智能体
            </a-button>
          </a-space>
        </div>

        <a-tabs v-model:activeKey="activeTab" class="persona-tabs">
          <a-tab-pane key="grid" tab="卡片视图">
            <a-spin :spinning="personaStore.loading">
              <div class="persona-grid-container">
                <div class="persona-grid">
                  <a-card
                    v-for="persona in paginatedPersonas"
                    :key="persona.id"
                    hoverable
                    class="persona-card"
                  >
                    <div class="card-header">
                      <div class="user-info">
                        <a-avatar :style="{ backgroundColor: getAvatarColor(persona.name) }" size="large">
                          {{ persona.name[0] }}
                        </a-avatar>
                        <div class="name-title">
                          <div class="name" :title="persona.name">{{ persona.name }}</div>
                          <div class="title" :title="persona.title || '暂无头衔'">{{ persona.title || '暂无头衔' }}</div>
                        </div>
                      </div>
                      <div class="actions">
                        <a-dropdown placement="bottomRight" :trigger="['click']">
                          <a-button type="text" size="small">
                            <template #icon><more-outlined /></template>
                          </a-button>
                          <template #overlay>
                            <a-menu>
                              <a-menu-item key="view" @click="showDetails(persona)">
                                <eye-outlined /> 查看详情
                              </a-menu-item>
                              <a-menu-item key="edit" @click="showModal(persona)">
                                <edit-outlined /> 编辑
                              </a-menu-item>
                              <a-menu-item key="delete" @click="showDeleteConfirm(persona)">
                                <span style="color: #ff4d4f"><delete-outlined /> 删除</span>
                              </a-menu-item>
                            </a-menu>
                          </template>
                        </a-dropdown>
                      </div>
                    </div>

                    <div class="persona-content">
                      <p class="bio" :title="persona.bio">{{ persona.bio || '暂无简介' }}</p>
                      <div class="stance" v-if="persona.stance">
                        <span class="label">立场:</span> {{ persona.stance }}
                      </div>
                      <div class="tags">
                        <a-tag v-if="persona.is_public" color="green">公开</a-tag>
                        <a-tag v-else color="blue">私有</a-tag>
                        <a-tag v-for="tag in persona.theories.slice(0, 2)" :key="tag">{{ tag }}</a-tag>
                        <a-tag v-if="persona.theories.length > 2">...</a-tag>
                      </div>
                    </div>
                  </a-card>
                
                <!-- Empty State -->
                <div v-if="personaStore.personas.length === 0" class="empty-state">
                  <a-empty description="暂无智能体，快去创建一个吧" />
                </div>
              </div>
              
              <div class="pagination-wrapper" v-if="personaStore.personas.length > 0">
                <a-pagination
                  v-model:current="currentPage"
                  v-model:pageSize="pageSize"
                  :total="personaStore.personas.length"
                  :show-size-changer="false"
                  @change="onPageChange"
                  align="center"
                />
              </div>
            </div>
          </a-spin>
        </a-tab-pane>
        
        <a-tab-pane key="list" tab="列表视图">
          <a-table
            :columns="columns"
            :data-source="personaStore.personas"
            :loading="personaStore.loading"
            row-key="id"
            tableLayout="fixed"
            :scroll="{ x: 1000 }"
            size="middle"
            :pagination="{ pageSize: 6, showSizeChanger: false, align: 'center' }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'bio'">
                <a-tooltip :title="record.bio">
                  <div class="table-text-ellipsis">{{ record.bio }}</div>
                </a-tooltip>
              </template>
              <template v-if="column.key === 'stance'">
                <a-tooltip :title="record.stance">
                  <div class="table-text-ellipsis">{{ record.stance }}</div>
                </a-tooltip>
              </template>
              <template v-if="column.key === 'theories'">
                <div class="table-tags">
                  <a-tag v-for="tag in record.theories.slice(0, 2)" :key="tag">{{ tag }}</a-tag>
                  <a-popover v-if="record.theories.length > 2">
                    <template #content>
                      <a-tag v-for="tag in record.theories.slice(2)" :key="tag" style="margin-bottom: 4px;">{{ tag }}</a-tag>
                    </template>
                    <a-tag>+{{ record.theories.length - 2 }}</a-tag>
                  </a-popover>
                </div>
              </template>
              <template v-if="column.key === 'is_public'">
                <a-tag :color="record.is_public ? 'green' : 'blue'">
                  {{ record.is_public ? '公开' : '私有' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="showDetails(record)">详情</a-button>
                  <a-button type="link" size="small" @click="showModal(record)">编辑</a-button>
                  <a-button type="link" size="small" danger @click="showDeleteConfirm(record)">删除</a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </div>

    <RealGodAgentModal
      v-model:open="realGodModalVisible"
    />

    <a-modal
      v-model:open="visible"
      :title="editingId ? '编辑智能体' : '创建智能体'"
      width="640px"
      @ok="handleOk"
      :confirmLoading="submitting"
    >
      <a-form
        layout="vertical"
        ref="formRef"
        :model="formState"
        class="persona-form"
      >
        <a-divider orientation="left">基本信息</a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="名称" name="name" :rules="[{ required: true, message: '请输入名称' }]">
              <a-input v-model:value="formState.name" placeholder="例如：苏格拉底" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="头衔" name="title">
              <a-input v-model:value="formState.title" placeholder="例如：古希腊哲学家" />
            </a-form-item>
          </a-col>
        </a-row>
        
        <a-form-item label="简介" name="bio">
          <a-textarea v-model:value="formState.bio" :rows="3" placeholder="简要描述智能体的背景和生平" />
        </a-form-item>

        <a-divider orientation="left">认知体系</a-divider>
        
        <a-form-item label="理论标签 (用逗号分隔)" name="theories_str">
          <a-input v-model:value="formState.theories_str" placeholder="例如：精神助产术, 辩证法, 讽刺" />
        </a-form-item>
        
        <a-form-item label="核心立场" name="stance">
          <a-input v-model:value="formState.stance" placeholder="例如：追求真理，质疑一切" />
        </a-form-item>

        <a-divider orientation="left">高级设置</a-divider>
        
        <a-form-item label="系统提示词 (System Prompt)" name="system_prompt">
          <a-textarea
            v-model:value="formState.system_prompt"
            :rows="4"
            placeholder="定义智能体在对话中的行为准则和指令"
          />
        </a-form-item>
        
        <a-form-item name="is_public">
          <a-checkbox v-model:checked="formState.is_public">
            设为公开智能体 (其他用户可见)
          </a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>

    <a-drawer
      v-model:open="detailsVisible"
      title="智能体详情"
      placement="right"
      width="600"
    >
      <template v-if="currentPersona">
        <a-descriptions bordered :column="1">
          <a-descriptions-item label="名称">{{ currentPersona.name }}</a-descriptions-item>
          <a-descriptions-item label="头衔">{{ currentPersona.title }}</a-descriptions-item>
          <a-descriptions-item label="核心立场">{{ currentPersona.stance }}</a-descriptions-item>
          <a-descriptions-item label="理论标签">
            <a-tag v-for="tag in currentPersona.theories" :key="tag">{{ tag }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="简介">
            <div style="white-space: pre-wrap;">{{ currentPersona.bio }}</div>
          </a-descriptions-item>
          <a-descriptions-item label="系统提示词">
            <div style="white-space: pre-wrap; font-family: monospace; background: #f5f5f5; padding: 8px; border-radius: 4px;">
              {{ currentPersona.system_prompt }}
            </div>
          </a-descriptions-item>
        </a-descriptions>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed, createVNode } from 'vue'
import { usePersonaStore, type Persona } from '@/stores/persona'
import { message, Modal } from 'ant-design-vue'
import RealGodAgentModal from '@/components/god/RealGodAgentModal.vue'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  GlobalOutlined,
  MoreOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons-vue'

const personaStore = usePersonaStore()
const visible = ref(false)
const detailsVisible = ref(false)
const realGodModalVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const activeTab = ref('grid')
const currentPersona = ref<Persona | null>(null)

// Pagination
const currentPage = ref(1)
const pageSize = ref(6)

const paginatedPersonas = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return personaStore.personas.slice(start, end)
})

const onPageChange = (page: number) => {
  currentPage.value = page
}

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
  { title: '头衔', dataIndex: 'title', key: 'title', width: 120 },
  { title: '简介', dataIndex: 'bio', key: 'bio', ellipsis: true, width: 200 },
  { title: '核心立场', dataIndex: 'stance', key: 'stance', width: 150 },
  { title: '理论标签', dataIndex: 'theories', key: 'theories', width: 200 },
  { title: '可见性', dataIndex: 'is_public', key: 'is_public', width: 80 },
  { title: '操作', key: 'action', width: 180 }
]

const formState = reactive({
  name: '',
  title: '',
  bio: '',
  theories_str: '',
  stance: '',
  system_prompt: '',
  is_public: false
})

onMounted(() => {
  personaStore.fetchPersonas()
})

const getAvatarColor = (name: string) => {
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#1890ff', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const showModal = (record?: Persona) => {
  visible.value = true
  if (record) {
    editingId.value = record.id
    Object.assign(formState, {
      ...record,
      theories_str: record.theories.join(', ')
    })
  } else {
    editingId.value = null
    Object.assign(formState, {
      name: '', title: '', bio: '', theories_str: '', stance: '', system_prompt: '', is_public: false
    })
  }
}

const handleOk = async () => {
  if (!formState.name) {
    message.warning('请输入智能体名称')
    return
  }

  submitting.value = true
  const data = {
    ...formState,
    theories: formState.theories_str.split(/[,，]/).map(s => s.trim()).filter(s => s)
  }
  
  try {
    if (editingId.value) {
      await personaStore.updatePersona(editingId.value, data)
      message.success('更新成功')
    } else {
      await personaStore.createPersona(data)
      message.success('创建成功')
    }
    visible.value = false
  } catch (e: unknown) {
    if (e instanceof Error) {
        message.error(e.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await personaStore.deletePersona(id)
    message.success('删除成功')
  } catch (e) {
    message.error('删除失败')
  }
}

const showDeleteConfirm = (persona: Persona) => {
  Modal.confirm({
    title: '确定要删除这个智能体吗？',
    icon: createVNode(ExclamationCircleOutlined),
    content: `删除后无法恢复：${persona.name}`,
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      await handleDelete(persona.id)
    }
  })
}

const showDetails = (persona: Persona) => {
  currentPersona.value = persona
  detailsVisible.value = true
}

const showRealGodModal = () => {
    realGodModalVisible.value = true
}
</script>

<style scoped>
.persona-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  border-bottom: 1px solid #333;
  padding-bottom: 16px;
}

.header-title {
  display: flex;
  flex-direction: column;
}

.title {
  font-weight: 600;
  font-size: 36px;
  font-weight: bold;
  color: #1890ff;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.subtitle {
  font-size: 14px;
  font-size: 14px;
  color: #888;
  margin-top: 4px;
  letter-spacing: 1px;
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.persona-card {
  background: rgba(15, 15, 20, 0.85);
  border: 1px solid #222;
  
  border-radius: 12px;
  transition: all 0.3s;
}

.persona-card:hover {
  border-color: #1890ff;
  box-shadow: 0 5px 20px rgba(24, 144, 255, 0.15);
  transform: translateY(-2px);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 16px;
}

.persona-avatar {
  background: #111;
  border: 1px solid #D4AF37;
  color: #1890ff;
  font-weight: 600;
  font-weight: bold;
}

.name {
  font-weight: 600;
  font-size: 20px;
  font-weight: bold;
  color: #F2E8CF;
  letter-spacing: 1px;
}

.persona-desc {
  font-size: 14px;
  font-size: 12px;
  color: #888;
  margin-top: 16px;
  line-height: 1.6;
  height: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.tags {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.type-tag {
  font-size: 14px;
  font-size: 10px;
  border: 1px solid #4CAF50;
  color: #4CAF50;
  background: rgba(76, 175, 80, 0.1);
  padding: 2px 6px;
}

.model-tag {
  font-size: 14px;
  font-size: 10px;
  border: 1px solid #1890ff;
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
  padding: 2px 6px;
}

:deep(.ant-modal-content) {
  background: #111 !important;
  border: 1px solid #D4AF37 !important;
  border-radius: 12px !important;
}

:deep(.ant-modal-header) {
  background: transparent !important;
  border-bottom: 1px solid #333 !important;
}

:deep(.ant-modal-title) {
  color: #D4AF37 !important;
  font-family: 'Cormorant Garamond', serif !important;
  font-size: 24px !important;
  letter-spacing: 2px !important;
}

:deep(.ant-modal-close-x) {
  color: #D4AF37 !important;
}

:deep(.ant-form-item-label > label) {
  color: #888 !important;
  font-family: 'Azeret Mono', monospace !important;
  font-size: 12px !important;
  letter-spacing: 1px;
}

.form-item-tip {
  font-size: 14px;
  font-size: 11px;
  color: #666;
  margin-top: 4px;
}
</style>
