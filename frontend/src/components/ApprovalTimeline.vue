<template>
  <div class="approval-timeline" v-loading="loading">
    <div v-if="records.length === 0 && !loading" class="empty-tip">暂无审批记录</div>
    <el-timeline v-else>
      <el-timeline-item
        v-for="record in records"
        :key="record.id"
        :type="getTimelineType(record.action)"
        :timestamp="formatTime(record.created_at)"
        placement="top"
        :hollow="false"
      >
        <div class="timeline-content">
          <div class="timeline-header">
            <el-tag :type="getTagType(record.action)" size="small" effect="light">
              {{ record.action_name }}
            </el-tag>
            <span class="operator">{{ record.operator_name }}</span>
          </div>
          <div v-if="record.comment" class="timeline-comment">{{ record.comment }}</div>
        </div>
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { approvalAPI } from '../api'

const props = defineProps({
  targetType: { type: String, required: true },
  targetId: { type: [Number, String], required: true }
})

const loading = ref(false)
const records = ref([])

const actionConfig = {
  submit: { timelineType: 'primary', tagType: 'info', label: '提交' },
  approve: { timelineType: 'success', tagType: 'success', label: '通过' },
  reject: { timelineType: 'danger', tagType: 'danger', label: '驳回' },
  return: { timelineType: 'warning', tagType: 'warning', label: '退回' }
}

function getTimelineType(action) {
  return actionConfig[action]?.timelineType || 'primary'
}

function getTagType(action) {
  return actionConfig[action]?.tagType || 'info'
}

function formatTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 19)
}

async function fetchRecords() {
  if (!props.targetId) return
  loading.value = true
  try {
    const res = await approvalAPI.list({
      target_type: props.targetType,
      target_id: props.targetId
    })
    if (res.data.code === 200) {
      records.value = res.data.data
    }
  } catch {
    records.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.targetId, fetchRecords, { immediate: true })
onMounted(fetchRecords)
</script>

<style scoped>
.approval-timeline {
  padding: 8px 0;
}

.empty-tip {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  text-align: center;
  padding: 16px 0;
}

.timeline-content {
  line-height: 1.6;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.operator {
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.timeline-comment {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  padding: 4px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}
</style>
