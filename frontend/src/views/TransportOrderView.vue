<template>
  <div>
    <PageGuide v-bind="guideConfig" />
<el-card>
      <template #header>
        <div class="card-header">
          <span>运输订单管理</span>
          <div>
            <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width:130px;margin-right:10px">
              <el-option label="待审核" value="pending" />
              <el-option label="已审核" value="approved" />
              <el-option label="已调度" value="dispatched" />
              <el-option label="运输中" value="in_transit" />
              <el-option label="已到达" value="arrived" />
              <el-option label="已完成" value="completed" />
            </el-select>
            <el-button type="success" @click="handleExport" style="margin-right:10px">导出数据</el-button>
            <el-button type="primary" @click="showCreateDialog">新建订单</el-button>
          </div>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" style="width:100%">
        <el-table-column prop="order_no" label="订单号" width="150" />
        <el-table-column prop="customer_name" label="客户" />
        <el-table-column prop="origin" label="发货地" />
        <el-table-column prop="destination" label="目的地" />
        <el-table-column prop="goods_name" label="货物" width="100" />
        <el-table-column prop="weight" label="重量(kg)" width="90" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vehicle_plate" label="车牌" width="100" />
        <el-table-column prop="driver_name" label="司机" width="80" />
            <el-table-column label="操作" width="320" fixed="right">
          <template #default="{row}">
            <el-button size="small" @click="viewDetail(row)">详情</el-button>
            <el-button v-if="row.status==='pending'" size="small" type="success" @click="handleApprove(row)">审核通过</el-button>
            <el-button v-if="row.status==='pending'" size="small" type="warning" @click="handleReturn(row)">退回</el-button>
            <el-button v-if="row.status==='pending'" size="small" type="danger" @click="handleReject(row)">驳回</el-button>
            <el-button v-if="row.status==='returned'" size="small" type="primary" @click="handleResubmit(row)">重新提交</el-button>
            <el-button v-if="row.status==='approved'" size="small" type="warning" @click="showDispatchDialog(row)">调度</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建订单弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建运输订单" width="550px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="客户" required>
          <el-select v-model="createForm.customer_id" placeholder="选择客户" filterable style="width:100%">
            <el-option v-for="c in customerList" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="发货地" required><el-input v-model="createForm.origin" /></el-form-item>
        <el-form-item label="目的地" required><el-input v-model="createForm.destination" /></el-form-item>
        <el-form-item label="货物名称"><el-input v-model="createForm.goods_name" /></el-form-item>
        <el-form-item label="重量(kg)"><el-input-number v-model="createForm.weight" :min="0" :precision="1" style="width:100%" /></el-form-item>
        <el-form-item label="体积(m³)"><el-input-number v-model="createForm.volume" :min="0" :precision="1" style="width:100%" /></el-form-item>
        <el-form-item label="件数"><el-input-number v-model="createForm.quantity" :min="1" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="createForm.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="submitting">创建</el-button>
      </template>
    </el-dialog>

    <!-- 调度弹窗 -->
    <el-dialog v-model="dispatchDialogVisible" title="车辆调度" width="500px">
      <el-form :model="dispatchForm" label-width="80px">
        <el-form-item label="选择车辆" required>
          <el-select v-model="dispatchForm.vehicle_id" placeholder="请选择空闲车辆" style="width:100%"
            :no-data-text="'暂无空闲车辆'">
            <el-option v-for="v in vehicleList" :key="v.id"
              :label="v.plate_no + ' (' + v.type + '，载重' + v.capacity_weight + 't)'"
              :value="v.id" />
          </el-select>
          <div v-if="vehicleList.length === 0" style="color:#f56c6c;font-size:12px;margin-top:4px">当前无空闲车辆</div>
        </el-form-item>
        <el-form-item label="选择司机" required>
          <el-select v-model="dispatchForm.driver_id" placeholder="请选择可用司机" style="width:100%"
            :no-data-text="'暂无可用司机'">
            <el-option v-for="d in driverList" :key="d.id"
              :label="d.name + ' (' + (d.phone||'') + '，' + (d.license_type||'') + ')'"
              :value="d.id" />
          </el-select>
          <div v-if="driverList.length === 0" style="color:#f56c6c;font-size:12px;margin-top:4px">当前无可用司机</div>
        </el-form-item>
        <el-form-item label="计划发车"><el-date-picker v-model="dispatchForm.plan_departure" type="datetime" style="width:100%" value-format="YYYY-MM-DD HH:mm" /></el-form-item>
        <el-form-item label="计划到达"><el-date-picker v-model="dispatchForm.plan_arrival" type="datetime" style="width:100%" value-format="YYYY-MM-DD HH:mm" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dispatchDialogVisible=false">取消</el-button>
        <el-button type="primary" @click="handleDispatch" :loading="submitting">确认调度</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import PageGuide from '../components/PageGuide.vue'

const guideConfig = { title: '运输订单操作指引', steps: [
        "创建运输订单",
        "审核通过后调度车辆和司机",
        "更新运输状态",
        "到达后签收确认"
    ], tips: [
        "调度时请选择空闲状态的车辆和可用司机",
        "签收后订单自动完成，车辆和司机释放"
    ] }
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { orderAPI, customerAPI, vehicleAPI, driverAPI } from '../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const list = ref([])
const customerList = ref([])
const vehicleList = ref([])
const driverList = ref([])
const loading = ref(false)
const submitting = ref(false)
const filterStatus = ref('')
const createDialogVisible = ref(false)
const dispatchDialogVisible = ref(false)
const currentOrderId = ref(null)
const createForm = ref({ customer_id:null, origin:'', destination:'', goods_name:'', weight:null, volume:null, quantity:null, remark:'' })
const dispatchForm = ref({ vehicle_id:null, driver_id:null, plan_departure:'', plan_arrival:'' })
const isMobile = ref(false)
const checkWidth = () => { isMobile.value = window.innerWidth < 768 }

const statusType = (s) => ({ pending:'warning', approved:'', returned:'warning', dispatched:'', in_transit:'primary', arrived:'success', signed:'', completed:'success', cancelled:'info' }[s]||'info')
const statusLabel = (s) => ({ pending:'待审核', approved:'已审核', returned:'已退回', dispatched:'已调度', in_transit:'运输中', arrived:'已到达', signed:'已签收', completed:'已完成', cancelled:'已取消' }[s]||s)

const loadData = async () => {
  loading.value = true
  try {
    const params = filterStatus.value ? { status: filterStatus.value } : {}
    const res = await orderAPI.list(params)
    if (res.data.code === 200) list.value = res.data.data
  } catch (e) { ElMessage.error('加载失败') }
  loading.value = false
}

const loadOptions = async () => {
  const r1 = await customerAPI.list()
  if (r1.data.code === 200) customerList.value = r1.data.data
}

// 打开调度弹窗时实时加载空闲车辆和可用司机
const loadDispatchOptions = async () => {
  const [r2, r3] = await Promise.all([
    vehicleAPI.list({ status: 'idle' }),
    driverAPI.list({ status: 'available' })
  ])
  if (r2.data.code === 200) vehicleList.value = r2.data.data
  if (r3.data.code === 200) driverList.value = r3.data.data
}

watch(filterStatus, loadData)

const showCreateDialog = () => {
  createForm.value = { customer_id:null, origin:'', destination:'', goods_name:'', weight:null, volume:null, quantity:null, remark:'' }
  createDialogVisible.value = true
}

const handleCreate = async () => {
  if (!createForm.value.customer_id || !createForm.value.origin || !createForm.value.destination)
    return ElMessage.warning('请填写必填项')
  submitting.value = true
  try {
    const res = await orderAPI.create(createForm.value)
    if (res.data.code === 200) { ElMessage.success('创建成功'); createDialogVisible.value = false; loadData() }
    else ElMessage.error(res.data.message)
  } catch (e) { ElMessage.error('创建失败') }
  submitting.value = false
}

const handleApprove = async (row) => {
  const res = await orderAPI.approve(row.id)
  if (res.data.code === 200) { ElMessage.success('审核通过'); loadData() }
}

const handleReturn = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入退回原因（必填）', '退回修改', {
      confirmButtonText: '退回',
      inputPlaceholder: '请填写退回原因',
      inputValidator: (v) => !!v || '退回原因不能为空',
      inputErrorMessage: '退回原因不能为空'
    })
    const res = await orderAPI.return(row.id, value)
    if (res.data.code === 200) { ElMessage.success('已退回'); loadData() }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const handleReject = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回', {
      confirmButtonText: '驳回',
      inputPlaceholder: '请填写驳回原因'
    })
    const res = await orderAPI.reject(row.id, value || '驳回')
    if (res.data.code === 200) { ElMessage.success('已驳回'); loadData() }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const handleResubmit = async (row) => {
  try {
    await ElMessageBox.confirm('确认重新提交该运输订单？', '重新提交', { type: 'info' })
    const res = await orderAPI.resubmit(row.id)
    if (res.data.code === 200) { ElMessage.success('已重新提交，等待审核'); loadData() }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const showDispatchDialog = async (row) => {
  currentOrderId.value = row.id
  dispatchForm.value = { vehicle_id:null, driver_id:null, plan_departure:'', plan_arrival:'' }
  vehicleList.value = []
  driverList.value = []
  dispatchDialogVisible.value = true
  await loadDispatchOptions()
}

const handleDispatch = async () => {
  if (!dispatchForm.value.vehicle_id || !dispatchForm.value.driver_id) return ElMessage.warning('请选择车辆和司机')
  submitting.value = true
  try {
    const res = await orderAPI.dispatch(currentOrderId.value, dispatchForm.value)
    if (res.data.code === 200) { ElMessage.success('调度成功'); dispatchDialogVisible.value = false; loadData() }
    else ElMessage.error(res.data.message)
  } catch (e) { ElMessage.error('调度失败') }
  submitting.value = false
}

const viewDetail = (row) => router.push(`/transport/orders/${row.id}`)

const handleExport = () => {
  window.open('/api/export/transport-orders?format=excel', '_blank')
}

onMounted(() => { checkWidth(); window.addEventListener('resize', checkWidth); loadData(); loadOptions() })
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
