<template>
  <div class="vehicle-view">
    <PageGuide v-bind="guideConfig" />
<el-card>
      <template #header>
        <div class="card-header">
          <span>车辆管理</span>
          <el-button type="primary" @click="showAddDialog">新增车辆</el-button>
        </div>
      </template>

      <el-table :data="vehicleList" style="width: 100%">
        <el-table-column prop="plate_no" label="车牌号" width="120" />
        <el-table-column prop="type" label="车型" width="100" />
        <el-table-column label="载重(吨)" width="110">
          <template #default="scope">
            {{ scope.row.capacity_weight || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="容积(立方米)" width="130">
          <template #default="scope">
            {{ scope.row.capacity_volume || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)" size="small">
              {{ statusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="showEditDialog(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增车辆' : '编辑车辆'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="车牌号" required>
          <el-input v-model="form.plate_no" placeholder="如：京A12345" />
        </el-form-item>
        <el-form-item label="车型" required>
          <el-select v-model="form.type" placeholder="请选择车型">
            <el-option label="小型" value="小型" />
            <el-option label="中型" value="中型" />
            <el-option label="大型" value="大型" />
            <el-option label="冷藏" value="冷藏" />
          </el-select>
        </el-form-item>
        <el-form-item label="载重(吨)">
          <el-input-number v-model="form.capacity_weight" :min="0" :precision="1" :step="0.5" />
        </el-form-item>
        <el-form-item label="容积(立方米)">
          <el-input-number v-model="form.capacity_volume" :min="0" :precision="1" :step="1" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="空闲" value="idle" />
            <el-option label="运输中" value="in_transport" />
            <el-option label="维护中" value="maintenance" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import PageGuide from '../components/PageGuide.vue'

const guideConfig = { title: '车辆管理操作指引', steps: [
        "新建车辆，填写车牌、类型等信息",
        "编辑或停用车辆"
    ], tips: [
        "车辆状态：空闲/在途/维护",
        "调度时只能选择空闲车辆"
    ] }
import { ref, onMounted, onUnmounted } from 'vue'
import { vehicleAPI } from '../api/common'
import { ElMessage, ElMessageBox } from 'element-plus'

const vehicleList = ref([])
const dialogVisible = ref(false)
const dialogType = ref('add')
const currentId = ref(null)
const defaultForm = {
  plate_no: '',
  type: '小型',
  capacity_weight: null,
  capacity_volume: null,
  status: 'idle'
}
const form = ref({ ...defaultForm })

const statusMap = {
  idle: '空闲',
  in_transport: '运输中',
  maintenance: '维护中',
  retired: '已退役'
}
const statusTagMap = {
  idle: 'success',
  in_transport: 'warning',
  maintenance: 'danger',
  retired: 'info'
}

const statusLabel = (status) => statusMap[status] || status
const statusTagType = (status) => statusTagMap[status] || 'info'

const isMobile = ref(false)
const checkWidth = () => { isMobile.value = window.innerWidth < 768 }

const loadData = async () => {
  try {
    const res = await vehicleAPI.list()
    if (res.data.code === 200) {
      vehicleList.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载失败')
  }
}

const showAddDialog = () => {
  dialogType.value = 'add'
  form.value = { ...defaultForm }
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  dialogType.value = 'edit'
  currentId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.plate_no || !form.value.type) {
    ElMessage.warning('车牌号和车型不能为空')
    return
  }
  try {
    let res
    if (dialogType.value === 'add') {
      res = await vehicleAPI.create(form.value)
    } else {
      res = await vehicleAPI.update(currentId.value, form.value)
    }
    if (res.data.code === 200) {
      ElMessage.success('保存成功')
      dialogVisible.value = false
      loadData()
    }
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该车辆吗？', '提示', { type: 'warning' })
    const res = await vehicleAPI.delete(row.id)
    if (res.data.code === 200) {
      ElMessage.success('删除成功')
      loadData()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  checkWidth()
  window.addEventListener('resize', checkWidth)
  loadData()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkWidth)
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
