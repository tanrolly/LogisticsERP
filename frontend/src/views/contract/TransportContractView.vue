<template>
  <div class="transport-contract-view">
    <PageGuide v-bind="guideConfig" />
<el-card>
      <template #header>
        <div class="card-header">
          <span>运输合同管理</span>
          <el-button type="primary" @click="showCreateDialog = true">
            从运输订单生成合同
          </el-button>
        </div>
      </template>

      <!-- 搜索筛选区 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable>
            <el-option label="待审批" value="pending" />
            <el-option label="已审批" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="生效中" value="active" />
            <el-option label="已完成" value="completed" />
            <el-option label="已终止" value="terminated" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadList">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 合同列表 -->
      <el-table :data="list" border stripe v-loading="loading">
        <el-table-column prop="contract_no" label="合同编号" width="150" />
        <el-table-column prop="order_no" label="运输订单号" width="150" />
        <el-table-column prop="customer_name" label="客户" width="150" />
        <el-table-column prop="freight_amount" label="运费金额" width="120">
          <template #default="{ row }">
            ¥{{ row.freight_amount?.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reviewer_name" label="审批人" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 'pending'"
              size="small"
              type="success"
              @click="handleApprove(row)"
            >审批通过</el-button>
            <el-button
              v-if="row.status === 'pending'"
              size="small"
              type="warning"
              @click="handleReturn(row)"
            >退回</el-button>
            <el-button
              v-if="row.status === 'pending'"
              size="small"
              type="danger"
              @click="handleReject(row)"
            >驳回</el-button>
            <el-button
              v-if="['approved', 'active'].includes(row.status)"
              size="small"
              type="warning"
              @click="handleTerminate(row)"
            >终止</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.per_page"
        :total="pagination.total"
        layout="total, prev, pager, next, jumper"
        @current-change="loadList"
        @size-change="loadList"
        class="pagination"
      />
    </el-card>

    <!-- 生成合同对话框 -->
    <el-dialog v-model="showCreateDialog" title="从运输订单生成合同" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="运输订单" required>
          <el-select v-model="createForm.order_id" placeholder="选择已审批的运输订单">
            <el-option
              v-for="order in eligibleOrders"
              :key="order.id"
              :label="`${order.order_no} - ¥${order.freight_amount?.toFixed(2)}`"
              :value="order.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="付款条款">
          <el-input v-model="createForm.payment_terms" type="textarea" rows="2" />
        </el-form-item>
        <el-form-item label="运输条款">
          <el-input v-model="createForm.transport_terms" type="textarea" rows="2" />
        </el-form-item>
        <el-form-item label="签订日期">
          <el-date-picker v-model="createForm.sign_date" type="date" placeholder="选择日期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 审批/驳回/退回对话框 -->
    <el-dialog v-model="showApproveDialog" :title="dialogTitle" width="500px">
      <el-form :model="approveForm">
        <el-form-item label="审批意见">
          <el-input v-model="approveForm.comment" type="textarea" rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApproveDialog = false">取消</el-button>
        <el-button type="primary" @click="submitApprove" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import PageGuide from '../../components/PageGuide.vue'

const guideConfig = { title: '运输合同操作指引', steps: [
        "创建运输合同",
        "提交审批",
        "审批通过后合同生效"
    ], tips: [
        "合同生效后可用于运输订单关联"
    ] }
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { transportContractAPI } from '../../api/contract'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const submitLoading = ref(false)
const list = ref([])
const eligibleOrders = ref([])

const searchForm = ref({
  status: ''
})

const pagination = ref({
  page: 1,
  per_page: 10,
  total: 0
})

const showCreateDialog = ref(false)
const createForm = ref({
  order_id: null,
  payment_terms: '',
  transport_terms: '',
  sign_date: ''
})

const showApproveDialog = ref(false)
const approveAction = ref('approve')
const approveForm = ref({
  id: null,
  comment: ''
})

const dialogTitle = computed(() => {
  const map = { approve: '审批通过', reject: '驳回合同', return: '退回修改' }
  return map[approveAction.value] || '审批操作'
})

const statusText = (status) => {
  const map = {
    'draft': '草稿',
    'pending': '待审批',
    'approved': '已审批',
    'rejected': '已驳回',
    'active': '生效中',
    'completed': '已完成',
    'terminated': '已终止'
  }
  return map[status] || status
}

const statusType = (status) => {
  const map = {
    'draft': 'info',
    'pending': 'warning',
    'approved': '',
    'rejected': 'danger',
    'active': 'success',
    'completed': 'success',
    'terminated': 'info'
  }
  return map[status] || ''
}

const loadList = async () => {
  loading.value = true
  try {
    const res = await transportContractAPI.getList({
      page: pagination.value.page,
      per_page: pagination.value.per_page,
      status: searchForm.value.status
    })
    if (res.data.code === 200) {
      list.value = res.data.data.items
      pagination.value.total = res.data.data.total
    }
  } finally {
    loading.value = false
  }
}

const loadEligibleOrders = async () => {
  try {
    const res = await transportContractAPI.getEligibleOrders()
    if (res.data.code === 200) {
      eligibleOrders.value = res.data.data
    }
  } catch (e) {
    console.error('加载可选订单失败', e)
  }
}

const resetSearch = () => {
  searchForm.value.status = ''
  loadList()
}

const viewDetail = (row) => {
  router.push(`/contract/detail/transport/${row.id}`)
}

const handleApprove = (row) => {
  approveAction.value = 'approve'
  approveForm.value = { id: row.id, comment: '' }
  showApproveDialog.value = true
}

const handleReturn = (row) => {
  approveAction.value = 'return'
  approveForm.value = { id: row.id, comment: '' }
  showApproveDialog.value = true
}

const handleReject = (row) => {
  approveAction.value = 'reject'
  approveForm.value = { id: row.id, comment: '' }
  showApproveDialog.value = true
}

const submitApprove = async () => {
  submitLoading.value = true
  try {
    let res
    if (approveAction.value === 'approve') {
      res = await transportContractAPI.approve(approveForm.value.id, { comment: approveForm.value.comment })
    } else if (approveAction.value === 'return') {
      res = await transportContractAPI.return(approveForm.value.id, { comment: approveForm.value.comment })
    } else {
      res = await transportContractAPI.reject(approveForm.value.id, { comment: approveForm.value.comment })
    }
    if (res.data.code === 200) {
      const msg = { approve: '审批通过', reject: '已驳回', return: '已退回' }[approveAction.value] || '操作成功'
      ElMessage.success(msg)
      showApproveDialog.value = false
      loadList()
    }
  } finally {
    submitLoading.value = false
  }
}

const handleTerminate = async (row) => {
  try {
    await ElMessageBox.confirm('确定终止该合同吗？', '提示', { type: 'warning' })
    const res = await transportContractAPI.terminate(row.id)
    if (res.data.code === 200) {
      ElMessage.success('合同已终止')
      loadList()
    }
  } catch (e) {
    // 用户取消
  }
}

const handleCreate = async () => {
  if (!createForm.value.order_id) {
    ElMessage.warning('请选择运输订单')
    return
  }
  submitLoading.value = true
  try {
    const data = { ...createForm.value }
    if (data.sign_date) data.sign_date = data.sign_date.toISOString().split('T')[0]
    const res = await transportContractAPI.create(data)
    if (res.data.code === 200) {
      ElMessage.success('合同创建成功，请等待审批')
      showCreateDialog.value = false
      loadList()
    }
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  loadList()
  loadEligibleOrders()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.search-form { margin-bottom: 16px; }
.pagination { margin-top: 16px; text-align: right; }
</style>
