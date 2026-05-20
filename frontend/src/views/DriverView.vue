<template>
  <div class="driver-view">
    <PageGuide v-bind="guideConfig" />
<el-card>
      <template #header>
        <div class="card-header">
          <span>司机管理</span>
          <el-button type="primary" @click="showAddDialog">新增司机</el-button>
        </div>
      </template>

      <el-table :data="driverList" style="width: 100%">
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="phone" label="电话" />
        <el-table-column prop="license_no" label="驾照号" />
        <el-table-column prop="license_type" label="驾照类型" width="100" />
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
    <el-dialog v-model="dialogVisible" :title="dialogType === 'add' ? '新增司机' : '编辑司机'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" placeholder="请输入电话号码" />
        </el-form-item>
        <el-form-item label="驾照号">
          <el-input v-model="form.license_no" placeholder="请输入驾照号" />
        </el-form-item>
        <el-form-item label="驾照类型">
          <el-select v-model="form.license_type" placeholder="请选择">
            <el-option label="A1" value="A1" />
            <el-option label="A2" value="A2" />
            <el-option label="B1" value="B1" />
            <el-option label="B2" value="B2" />
            <el-option label="C1" value="C1" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="可用" value="available" />
            <el-option label="在途" value="on_road" />
            <el-option label="休息" value="off_duty" />
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

const guideConfig = { title: '司机管理操作指引', steps: [
        "新建司机，填写姓名、驾照信息",
        "编辑或管理司机"
    ], tips: [
        "司机状态：可用/在途/休息",
        "调度时只能选择可用司机"
    ] }
import { ref, onMounted, onUnmounted } from 'vue'
import { driverAPI } from '../api/common'
import { ElMessage, ElMessageBox } from 'element-plus'

const driverList = ref([])
const dialogVisible = ref(false)
const dialogType = ref('add')
const currentId = ref(null)
const defaultForm = {
  name: '',
  phone: '',
  license_no: '',
  license_type: '',
  status: 'available'
}
const form = ref({ ...defaultForm })

const statusMap = {
  available: '可用',
  on_road: '在途',
  off_duty: '休息',
  dismissed: '已离职'
}
const statusTagMap = {
  available: 'success',
  on_road: 'warning',
  off_duty: 'info',
  dismissed: 'danger'
}

const statusLabel = (status) => statusMap[status] || status
const statusTagType = (status) => statusTagMap[status] || 'info'

const isMobile = ref(false)
const checkWidth = () => { isMobile.value = window.innerWidth < 768 }

const loadData = async () => {
  try {
    const res = await driverAPI.list()
    if (res.data.code === 200) {
      driverList.value = res.data.data
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
  if (!form.value.name) {
    ElMessage.warning('司机姓名不能为空')
    return
  }
  try {
    let res
    if (dialogType.value === 'add') {
      res = await driverAPI.create(form.value)
    } else {
      res = await driverAPI.update(currentId.value, form.value)
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
    await ElMessageBox.confirm('确定删除该司机吗？', '提示', { type: 'warning' })
    const res = await driverAPI.delete(row.id)
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
