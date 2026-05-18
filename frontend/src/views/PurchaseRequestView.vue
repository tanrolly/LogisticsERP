<template>
  <div>
    <PageGuide v-bind="guideConfig" />
<el-card>
      <template #header>
        <div class="card-header">
          <span>采购申请管理</span>
          <div>
            <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width:140px;margin-right:10px">
              <el-option label="待审批" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已退回" value="returned" />
              <el-option label="已驳回" value="rejected" />
            </el-select>
            <el-button type="primary" @click="showCreateDialog">新建申请</el-button>
          </div>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" style="width:100%">
        <el-table-column prop="req_no" label="申请单号" width="160" />
        <el-table-column prop="goods_name" label="商品名称" />
        <el-table-column prop="goods_sku" label="SKU" width="100" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="est_unit_price" label="期望单价" width="100">
          <template #default="{row}">{{ row.est_unit_price ? '¥' + row.est_unit_price : '-' }}</template>
        </el-table-column>
        <el-table-column prop="est_total_price" label="期望总价" width="110">
          <template #default="{row}">{{ row.est_total_price ? '¥' + row.est_total_price : '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="applicant_name" label="申请人" width="100" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{row}">
            <el-button size="small" @click="showDetail(row)">详情</el-button>
            <el-button v-if="row.status==='pending'" size="small" type="success" @click="handleApprove(row)">通过</el-button>
            <el-button v-if="row.status==='pending'" size="small" type="warning" @click="handleReturn(row)">退回</el-button>
            <el-button v-if="row.status==='pending'" size="small" type="danger" @click="handleReject(row)">驳回</el-button>
            <el-button v-if="row.status==='returned'" size="small" type="primary" @click="handleResubmit(row)">重新提交</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建申请弹窗 -->
    <el-dialog v-model="dialogVisible" title="新建采购申请" width="500px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="商品" required>
          <el-select v-model="form.goods_id" placeholder="选择商品" filterable style="width:100%">
            <el-option v-for="g in goodsList" :key="g.id" :label="g.name + '(' + g.sku + ')'" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="form.quantity" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="期望单价">
          <el-input-number v-model="form.est_unit_price" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="紧急程度">
          <el-radio-group v-model="form.urgency">
            <el-radio value="normal">普通</el-radio>
            <el-radio value="urgent">紧急</el-radio>
            <el-radio value="critical">特急</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="申请原因">
          <el-input v-model="form.reason" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="采购申请详情" size="480px">
      <template v-if="detailData">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="申请单号">{{ detailData.req_no }}</el-descriptions-item>
          <el-descriptions-item label="商品">{{ detailData.goods_name }} ({{ detailData.goods_sku }})</el-descriptions-item>
          <el-descriptions-item label="数量">{{ detailData.quantity }}</el-descriptions-item>
          <el-descriptions-item label="期望单价">{{ detailData.est_unit_price ? '¥' + detailData.est_unit_price : '-' }}</el-descriptions-item>
          <el-descriptions-item label="期望总价">{{ detailData.est_total_price ? '¥' + detailData.est_total_price : '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(detailData.status)">{{ statusLabel(detailData.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="申请人">{{ detailData.applicant_name }}</el-descriptions-item>
          <el-descriptions-item label="紧急程度">{{ detailData.urgency === 'normal' ? '普通' : detailData.urgency === 'urgent' ? '紧急' : '特急' }}</el-descriptions-item>
          <el-descriptions-item label="申请原因">{{ detailData.reason || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.review_comment" label="审批意见">{{ detailData.review_comment }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.reviewer_name" label="审批人">{{ detailData.reviewer_name }}</el-descriptions-item>
          <el-descriptions-item v-if="detailData.reviewed_at" label="审批时间">{{ detailData.reviewed_at?.replace('T', ' ').slice(0,19) }}</el-descriptions-item>
        </el-descriptions>

        <h4 style="margin: 20px 0 12px">审批记录</h4>
        <ApprovalTimeline target-type="purchase_request" :target-id="detailData.id" />
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import PageGuide from '../components/PageGuide.vue'
import ApprovalTimeline from '../components/ApprovalTimeline.vue'

const guideConfig = { title: '采购申请操作指引', steps: [
        "新建采购申请，选择商品并填写数量",
        "等待审批通过",
        "审批通过后可生成采购订单"
    ], tips: [
        "需选择具体商品和数量才能提交",
        "审批通过后系统自动创建采购订单"
    ] }
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { purchaseRequestAPI, goodsAPI } from '../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const list = ref([])
const goodsList = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const filterStatus = ref('')
const form = ref({ goods_id: null, quantity: 100, est_unit_price: null, urgency: 'normal', reason: '' })
const isMobile = ref(false)
const checkWidth = () => { isMobile.value = window.innerWidth < 768 }

const drawerVisible = ref(false)
const detailData = ref(null)

const statusType = (s) => ({ pending: 'warning', approved: 'success', returned: 'warning', rejected: 'danger', cancelled: 'info' }[s] || 'info')
const statusLabel = (s) => ({ pending: '待审批', approved: '已通过', returned: '已退回', rejected: '已驳回', cancelled: '已取消' }[s] || s)

const loadData = async () => {
  loading.value = true
  try {
    const params = filterStatus.value ? { status: filterStatus.value } : {}
    const res = await purchaseRequestAPI.list(params)
    if (res.data.code === 200) list.value = res.data.data
  } catch (e) { ElMessage.error('加载失败') }
  loading.value = false
}

const loadGoods = async () => {
  const res = await goodsAPI.list()
  if (res.data.code === 200) goodsList.value = res.data.data
}

watch(filterStatus, loadData)

const showCreateDialog = () => {
  form.value = { goods_id: null, quantity: 100, est_unit_price: null, urgency: 'normal', reason: '' }
  dialogVisible.value = true
}

const handleCreate = async () => {
  if (!form.value.goods_id || !form.value.quantity) return ElMessage.warning('请填写商品和数量')
  submitting.value = true
  try {
    const res = await purchaseRequestAPI.create(form.value)
    if (res.data.code === 200) {
      ElMessage.success('提交成功')
      dialogVisible.value = false
      loadData()
    } else { ElMessage.error(res.data.message) }
  } catch (e) { ElMessage.error('提交失败') }
  submitting.value = false
}

const handleApprove = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入审批意见', '审批通过', { confirmButtonText: '通过', inputPlaceholder: '同意' })
    const res = await purchaseRequestAPI.approve(row.id, value || '同意')
    if (res.data.code === 200) { ElMessage.success('审批通过'); loadData() }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const handleReturn = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入退回原因（必填）', '退回修改', {
      confirmButtonText: '退回',
      inputPlaceholder: '请填写退回原因',
      inputValidator: (v) => !!v || '退回原因不能为空',
      inputErrorMessage: '退回原因不能为空'
    })
    const res = await purchaseRequestAPI.return(row.id, value)
    if (res.data.code === 200) { ElMessage.success('已退回'); loadData() }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const handleReject = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回', { confirmButtonText: '驳回', inputPlaceholder: '请填写驳回原因' })
    const res = await purchaseRequestAPI.reject(row.id, value || '驳回')
    if (res.data.code === 200) { ElMessage.success('已驳回'); loadData() }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const handleResubmit = async (row) => {
  try {
    await ElMessageBox.confirm('确认重新提交该申请？', '重新提交', { type: 'info' })
    const res = await purchaseRequestAPI.resubmit(row.id)
    if (res.data.code === 200) { ElMessage.success('已重新提交，等待审批'); loadData() }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const showDetail = async (row) => {
  const res = await purchaseRequestAPI.get(row.id)
  if (res.data.code === 200) { detailData.value = res.data.data; drawerVisible.value = true }
}

onMounted(() => { checkWidth(); window.addEventListener('resize', checkWidth); loadData(); loadGoods() })
onUnmounted(() => { window.removeEventListener('resize', checkWidth) })
</script>

<style scoped>
.card-header { display:flex; justify-content:space-between; align-items:center; }
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
