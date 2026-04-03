<template>
  <div class="page-wrapper">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">智能体工坊</h1>
        <p class="page-subtitle">管理与配置可参与讨论的虚拟智能体实体。</p>
      </div>
      <div class="header-right">
        <a-button @click="handleCreatePresets" :loading="creatingPresets" size="large" class="preset-btn" style="margin-right: 12px;">
          <thunderbolt-outlined /> 一键生成预设库
        </a-button>
        <a-button type="primary" size="large" @click="showCreateModal" class="create-btn">
          <plus-outlined /> 新建智能体
        </a-button>
      </div>
    </div>

    <div class="content-body">
      <div v-if="personaStore.loading" class="state-container">
        <a-spin size="large" />
      </div>

      <div v-else-if="personaStore.personas.length === 0" class="empty-state">
        <div class="empty-icon"><team-outlined /></div>
        <h3>无可用智能体</h3>
        <p>您还没有创建任何智能体，请点击右上角按钮新建一个。</p>
        <a-button type="primary" @click="showCreateModal">立即创建</a-button>
      </div>

      <div v-else class="persona-grid">
        <div 
          v-for="p in personaStore.personas" 
          :key="p.id" 
          class="persona-card"
          @click="editPersona(p)"
        >
          <div class="card-header">
            <div class="avatar-box">{{ p.name[0] }}</div>
            <div class="card-actions" @click.stop>
              <a-popconfirm title="确定要删除此智能体吗？" @confirm="handleDelete(p.id)">
                <a-button type="text" danger shape="circle">
                  <delete-outlined />
                </a-button>
              </a-popconfirm>
            </div>
          </div>
          
          <div class="card-body">
            <h3 class="persona-name">{{ p.name }}</h3>
            <p class="persona-desc">{{ p.description || '暂无描述' }}</p>
          </div>
          
          <div class="card-footer">
            <div class="tags">
              <span class="tag-model"><api-outlined /> {{ p.model }}</span>
              <span class="tag-type" v-if="p.persona_type"><tag-outlined /> {{ p.persona_type }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <a-drawer
      v-model:open="isModalVisible"
      :title="editingId ? '编辑智能体配置' : '新建自定义智能体配置'"
      width="500"
      placement="right"
      :footer-style="{ textAlign: 'right' }"
      destroyOnClose
    >
      <a-form layout="vertical" :model="formState" @finish="handleSave">
        <a-form-item 
          label="智能体名称" 
          name="name" 
          :rules="[{ required: true, message: '请输入名称' }]"
        >
          <a-input v-model:value="formState.name" placeholder="例如：架构师、代码审查员..." size="large" />
        </a-form-item>

        <a-form-item 
          label="智能体系统提示词 (System Prompt)" 
          name="system_prompt" 
          :rules="[{ required: true, message: '请输入系统提示词' }]"
        >
          <a-textarea 
            v-model:value="formState.system_prompt" 
            :rows="6" 
            placeholder="定义该智能体的角色、语气和行为规范..." 
          />
          <div class="form-hint">提示词越详细，智能体的表现越符合预期。</div>
        </a-form-item>

        <a-form-item label="大语言模型 (Model)" name="model">
          <a-select v-model:value="formState.model" size="large">
            <a-select-option value="gpt-3.5-turbo">GPT-3.5-Turbo</a-select-option>
            <a-select-option value="gpt-4">GPT-4</a-select-option>
            <a-select-option value="gpt-4-turbo">GPT-4-Turbo</a-select-option>
            <a-select-option value="claude-3-haiku">Claude 3 Haiku</a-select-option>
            <a-select-option value="claude-3-sonnet">Claude 3 Sonnet</a-select-option>
            <a-select-option value="claude-3-opus">Claude 3 Opus</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="简短描述 (Description)" name="description">
          <a-input v-model:value="formState.description" placeholder="一句话概括该智能体的特征..." size="large" />
        </a-form-item>

        <a-form-item label="分类标签 (Type)" name="persona_type">
          <a-input v-model:value="formState.persona_type" placeholder="例如：技术、运营、产品..." size="large" />
        </a-form-item>

        <div class="drawer-footer">
          <a-button @click="isModalVisible = false" style="margin-right: 8px">取消</a-button>
          <a-button type="primary" html-type="submit" :loading="saving">保存配置</a-button>
        </div>
      </a-form>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'
import { 
  PlusOutlined, ThunderboltOutlined, 
  TeamOutlined, 
  DeleteOutlined,
  ApiOutlined,
  TagOutlined
} from '@ant-design/icons-vue'

const personaStore = usePersonaStore()
const authStore = useAuthStore()

const isModalVisible = ref(false)
const saving = ref(false)
const editingId = ref<string | null>(null)
const creatingPresets = ref(false)

const handleCreatePresets = async () => {
  try {
    creatingPresets.value = true
    await personaStore.createPresetPersonas()
    message.success('预设智能体生成成功')
  } catch (error: any) {
    message.error(error.message || '生成失败')
  } finally {
    creatingPresets.value = false
  }
}

const formState = reactive({
  name: '',
  system_prompt: '',
  model: 'gpt-3.5-turbo',
  description: '',
  persona_type: ''
})

const resetForm = () => {
  editingId.value = null
  formState.name = ''
  formState.system_prompt = ''
  formState.model = 'gpt-3.5-turbo'
  formState.description = ''
  formState.persona_type = ''
}

const showCreateModal = () => {
  resetForm()
  isModalVisible.value = true
}

const editPersona = (p: any) => {
  editingId.value = p.id
  formState.name = p.name
  formState.system_prompt = p.system_prompt
  formState.model = p.model || 'gpt-3.5-turbo'
  formState.description = p.description || ''
  formState.persona_type = p.persona_type || ''
  isModalVisible.value = true
}

const handleSave = async () => {
  try {
    saving.value = true
    const payload = {
      ...formState,
      creator_id: authStore.user?.id
    }
    
    if (editingId.value) {
      await personaStore.updatePersona(editingId.value, payload)
      message.success('更新成功')
    } else {
      await personaStore.createPersona(payload)
      message.success('创建成功')
    }
    isModalVisible.value = false
    await personaStore.fetchPersonas(authStore.user?.id)
  } catch (error: any) {
    message.error(error.message || '操作失败')
  } finally {
    saving.value = false
  }
}

const handleDelete = async (id: string) => {
  try {
    await personaStore.deletePersona(id)
    message.success('删除成功')
    await personaStore.fetchPersonas(authStore.user?.id)
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

onMounted(() => {
  personaStore.fetchPersonas(authStore.user?.id)
})
</script>

<style scoped>
.page-wrapper {
  max-width: 1440px;
  margin: 0 auto;
  padding: 32px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 40px;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}

.page-subtitle {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.45);
  margin: 0;
}

.create-btn {
  height: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.2);
}

.state-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  color: rgba(255, 255, 255, 0.2);
  margin-bottom: 16px;
}

.empty-state h3 {
  font-size: 20px;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 8px;
}

.empty-state p {
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 24px;
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

.persona-card {
  background: rgba(25, 25, 35, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.persona-card:hover {
  background: rgba(25, 25, 35, 0.9);
  border-color: rgba(22, 119, 255, 0.3);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  transform: translateY(-4px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.avatar-box {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #722ed1 0%, #2f54eb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(114, 46, 209, 0.3);
}

.card-actions {
  opacity: 0;
  transition: opacity 0.2s;
}

.persona-card:hover .card-actions {
  opacity: 1;
}

.card-body {
  flex: 1;
}

.persona-name {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 8px;
}

.persona-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
  line-height: 1.6;
  margin-bottom: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag-model, .tag-type {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.tag-model {
  background: rgba(22, 119, 255, 0.1);
  color: #1677ff;
  border: 1px solid rgba(22, 119, 255, 0.2);
}

.tag-type {
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.2);
}

/* Drawer styles overrides */
.form-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  margin-top: 8px;
}

.drawer-footer {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 100%;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px 24px;
  background: #141414;
  text-align: right;
  z-index: 1;
}

:deep(.ant-drawer-content) {
  background-color: #141414;
}

:deep(.ant-drawer-header) {
  background: transparent;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

:deep(.ant-drawer-title) {
  color: #ffffff;
  font-weight: 600;
}

:deep(.ant-form-item-label > label) {
  color: rgba(255, 255, 255, 0.85);
  font-weight: 500;
}

@media (max-width: 768px) {
  .page-wrapper {
    padding: 24px 16px;
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  .persona-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<style scoped>
.preset-btn {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  border-radius: 8px;
  box-shadow: none;
}

.preset-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}
</style>
