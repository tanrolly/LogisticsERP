<template>
  <div v-loading="loading">
    <PageGuide v-bind="guideConfig" />
<el-page-header @back="$router.push('/transport/orders')" title="返回列表" style="margin-bottom:20px" />

    <!-- 步骤条 -->
    <el-card style="margin-bottom:20px">
      <el-steps :active="stepIndex" align-center>
        <el-step title="待审核" />
        <el-step title="已审核" />
        <el-step title="已调度" />
        <el-step title="运输中" />
        <el-step title="已到达" />
        <el-step title="已签收" />
        <el-step title="已完成" />
      </el-steps>
    </el-card>

    <!-- 基本信息 -->
    <el-card style="margin-bottom:20px">
      <template #header><span>订单信息</span></template>
      <el-descriptions :column="isMobile ? 1 : 3" border v-if="order">
        <el-descriptions-item label="订单号">{{ order.order_no }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ order.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType(order.status)">{{ statusLabel(order.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="发货地">{{ order.origin }}</el-descriptions-item>
        <el-descriptions-item label="目的地">{{ order.destination }}</el-descriptions-item>
        <el-descriptions-item label="货物">{{ order.goods_name }}</el-descriptions-item>
        <el-descriptions-item label="重量">{{ order.weight }} kg</el-descriptions-item>
        <el-descriptions-item label="体积">{{ order.volume }} m³</el-descriptions-item>
        <el-descriptions-item label="件数">{{ order.quantity }}</el-descriptions-item>
        <el-descriptions-item label="车牌">{{ order.vehicle_plate || '-' }}</el-descriptions-item>
        <el-descriptions-item label="司机">{{ order.driver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="运费">¥{{ order.freight_amount || '待计算' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 审批记录 -->
    <el-card style="margin-bottom:20px">
      <template #header><span>审批记录</span></template>
      <ApprovalTimeline target-type="transport_order" :target-id="order?.id" />
    </el-card>

    <!-- 操作按钮 -->
    <el-card style="margin-bottom:20px">
      <template #header><span>操作</span></template>
      <el-button v-if="order && order.status === 'dispatched'" type="primary" @click="addRecord('in_transit')">更新：正在运输</el-button>
      <el-button v-if="order && order.status === 'in_transit'" type="success" @click="addRecord('arrived')">更新：已到达</el-button>
      <el-button v-if="order && order.status === 'arrived'" type="warning" @click="showPodDialog = true">POD 签收确认</el-button>
      <el-button v-if="order && order.status === 'signed'" type="success" @click="completeOrder">完成订单</el-button>
      <el-button v-if="order && ['dispatched','in_transit','arrived'].includes(order.status)" type="danger" @click="showExceptionDialog = true">登记异常</el-button>
      <el-button v-if="order" @click="viewFreight" style="margin-left:10px">查看运费</el-button>
    </el-card>

    <!-- 跟踪时间线 -->
    <el-card>
      <template #header><span>运输跟踪记录</span></template>
      <el-timeline v-if="records.length">
        <el-timeline-item v-for="rec in records" :key="rec.id"
          :timestamp="rec.recorded_at?.substring(0,19)" placement="top" :type="timelineType(rec.status)">
          <el-card shadow="never">
            <h4>{{ statusLabel(rec.status) }}</h4>
            <p>位置：{{ rec.location }}</p>
            <p>描述：{{ rec.description }}</p>
            <p style="color:#909399;font-size:12px">记录人：{{ rec.recorder_name }}</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无跟踪记录" />
    </el-card>

    <!-- 异常记录列表 -->
    <el-card style="margin-top:20px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>运输异常记录</span>
          <el-button v-if="order && ['dispatched','in_transit','arrived'].includes(order.status)" 
                     type="danger" size="small" @click="showExceptionDialog = true">登记异常</el-button>
        </div>
      </template>
      <el-table :data="exceptions" style="width:100%" v-if="exceptions.length">
        <el-table-column prop="exception_type" label="异常类型" width="100">
          <template #default="{row}">
            <el-tag :type="exceptionTypeTag(row.exception_type)">{{ exceptionTypeLabel(row.exception_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重程度" width="90">
          <template #default="{row}">
            <el-tag :type="severityTag(row.severity)">{{ severityLabel(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="异常描述" />
        <el-table-column prop="location" label="地点" width="150" />
        <el-table-column prop="handle_status" label="处理状态" width="100">
          <template #default="{row}">
            <el-tag :type="handleStatusTag(row.handle_status)">{{ handleStatusLabel(row.handle_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reported_at" label="登记时间" width="160" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{row}">
            <el-button v-if="row.handle_status === 'pending'" type="primary" size="small" 
                       @click="openHandleDialog(row)">处理</el-button>
            <el-button v-if="row.handle_status === 'pending'" type="danger" size="small" 
                       @click="deleteException(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无异常记录" />
    </el-card>

    <!-- POD 签收确认对话框 -->
    <el-dialog v-model="showPodDialog" title="POD 签收确认" width="500px">
      <el-form :model="podForm" label-width="100px">
        <el-form-item label="签收人姓名" required>
          <el-input v-model="podForm.signee_name" placeholder="请输入签收人姓名" />
        </el-form-item>
        <el-form-item label="签收人电话">
          <el-input v-model="podForm.signee_phone" placeholder="请输入签收人电话" />
        </el-form-item>
        <el-form-item label="POD 图片">
          <el-input v-model="podForm.pod_image" placeholder="模拟上传，输入图片路径" />
          <div style="color:#909399;font-size:12px;margin-top:5px">教学模拟：直接输入图片文件名，如 pod001.jpg</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPodDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmPod">确认签收</el-button>
      </template>
    </el-dialog>

    <!-- 新增：完成订单对话框 -->
    <el-dialog v-model="showCompleteDialog" title="完成订单" width="500px">
      <el-form :model="completeForm" label-width="100px">
        <el-form-item label="系统计算运费">
          <el-input :value="order?.freight_amount || 0" disabled>
            <template #append>元</template>
          </el-input>
          <div style="color:#909399;font-size:12px;margin-top:5px">
            系统根据重量和体积自动计算
          </div>
        </el-form-item>
  
        <el-form-item label="实际运费">
          <el-input-number 
            v-model="completeForm.actual_freight" 
            :min="0" 
            :precision="2"
            :step="10"
            placeholder="请输入实际运费"
            style="width: 100%"
          />
          <div style="color:#E6A23C;font-size:12px;margin-top:5px">
            如果实际运费与系统计算不一致，可以在这里修改
          </div>
        </el-form-item>
  
        <el-form-item label="备注说明">
          <el-input 
            v-model="completeForm.remark" 
            type="textarea" 
            :rows="3"
            placeholder="如有特殊情况，请在此说明（选填）" 
          />
        </el-form-item>
      </el-form>
  
      <template #footer>
        <el-button @click="showCompleteDialog = false">取消</el-button>
        <el-button type="primary" @click="submitComplete" :loading="completing">
          确认完成订单
        </el-button>
      </template>
    </el-dialog>

    <!-- 异常登记对话框 -->
    <el-dialog v-model="showExceptionDialog" title="登记运输异常" width="500px">
      <el-form :model="exceptionForm" label-width="100px">
        <el-form-item label="异常类型" required>
          <el-select v-model="exceptionForm.exception_type" placeholder="请选择异常类型" style="width:100%">
            <el-option label="货物破损" value="damage" />
            <el-option label="运输延误" value="delay" />
            <el-option label="货物丢失" value="loss" />
            <el-option label="客户拒收" value="reject" />
            <el-option label="交通事故" value="accident" />
            <el-option label="车辆故障" value="breakdown" />
            <el-option label="其他异常" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="exceptionForm.severity" placeholder="请选择严重程度" style="width:100%">
            <el-option label="轻微" value="low" />
            <el-option label="一般" value="normal" />
            <el-option label="严重" value="high" />
            <el-option label="重大" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="异常地点">
          <el-input v-model="exceptionForm.location" placeholder="请输入异常发生地点" />
        </el-form-item>
        <el-form-item label="异常描述" required>
          <el-input v-model="exceptionForm.description" type="textarea" :rows="3" placeholder="请详细描述异常情况" />
        </el-form-item>
        <el-form-item label="异常照片">
          <el-input v-model="exceptionForm.image" placeholder="模拟上传，输入图片路径" />
          <div style="color:#909399;font-size:12px;margin-top:5px">教学模拟：直接输入图片文件名，如 exception001.jpg</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExceptionDialog = false">取消</el-button>
        <el-button type="primary" @click="createException">确认登记</el-button>
      </template>
    </el-dialog>

    <!-- 异常处理对话框 -->
    <el-dialog v-model="showHandleDialog" title="处理运输异常" width="500px">
      <el-form :model="handleForm" label-width="100px">
        <el-form-item label="处理状态" required>
          <el-select v-model="handleForm.handle_status" placeholder="请选择处理状态" style="width:100%">
            <el-option label="处理中" value="processing" />
            <el-option label="已解决" value="resolved" />
            <el-option label="关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理备注">
          <el-input v-model="handleForm.handle_note" type="textarea" :rows="3" placeholder="请输入处理备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showHandleDialog = false">取消</el-button>
        <el-button type="primary" @click="handleException">确认处理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import PageGuide from '../components/PageGuide.vue'
import ApprovalTimeline from '../components/ApprovalTimeline.vue'

const guideConfig = { title: '运输订单详情操作指引', steps: [
        "查看订单基本信息",
        "查看运输记录",
        "执行签收或查看POD"
    ], tips: [
        "签收后不可撤销",
        "完成订单后自动计算运费和生成应收账款"
    ] }
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { orderAPI, transportRecordAPI, exceptionAPI } from '../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const order = ref(null)
const records = ref([])
const exceptions = ref([])
const loading = ref(false)
const isMobile = ref(false)
const showPodDialog = ref(false)
const showCompleteDialog = ref(false)  // 新增：完成订单对话框显示状态
const completing = ref(false)  // 新增：完成订单提交状态
const showExceptionDialog = ref(false)
const showHandleDialog = ref(false)
const podForm = reactive({ signee_name: '', signee_phone: '', pod_image: '' })
// 新增：完成订单表单
const completeForm = reactive({ actual_freight: null, remark: '' })
const exceptionForm = reactive({ exception_type: '', severity: 'normal', location: '', description: '', image: '' })
const handleForm = reactive({ id: null, handle_status: 'processing', handle_note: '' })
const checkWidth = () => { isMobile.value = window.innerWidth < 768 }

const statusMap = ['pending','approved','dispatched','in_transit','arrived','signed','completed']
const stepIndex = computed(() => order.value ? statusMap.indexOf(order.value.status) : 0)

const statusType = (s) => ({ pending:'warning', returned:'warning', approved:'', dispatched:'', in_transit:'primary', arrived:'success', signed:'', completed:'success', cancelled:'info' }[s]||'info')
const statusLabel = (s) => ({ pending:'待审核', returned:'已退回', approved:'已审核', dispatched:'已调度', in_transit:'运输中', arrived:'已到达', signed:'已签收', completed:'已完成', cancelled:'已取消' }[s]||s)
const timelineType = (s) => ({ departed:'primary', in_transit:'primary', arrived:'success', signed:'success' }[s]||'info')

// 异常类型映射
const exceptionTypeLabel = (t) => ({ damage:'货物破损', delay:'运输延误', loss:'货物丢失', reject:'客户拒收', accident:'交通事故', breakdown:'车辆故障', other:'其他' }[t]||t)
const exceptionTypeTag = (t) => ({ damage:'warning', delay:'', loss:'danger', reject:'warning', accident:'danger', breakdown:'', other:'' }[t]||'info')

// 严重程度映射
const severityLabel = (s) => ({ low:'轻微', normal:'一般', high:'严重', critical:'重大' }[s]||s)
const severityTag = (s) => ({ low:'success', normal:'', high:'warning', critical:'danger' }[s]||'info')

// 处理状态映射
const handleStatusLabel = (s) => ({ pending:'待处理', processing:'处理中', resolved:'已解决', closed:'已关闭' }[s]||s)
const handleStatusTag = (s) => ({ pending:'warning', processing:'primary', resolved:'success', closed:'info' }[s]||'info')

const loadData = async () => {
  loading.value = true
  const id = route.params.id
  const [r1, r2, r3] = await Promise.all([
    orderAPI.get(id),
    transportRecordAPI.list({ order_id: id }),
    exceptionAPI.list({ order_id: id })
  ])
  if (r1.data.code === 200) order.value = r1.data.data
  if (r2.data.code === 200) records.value = r2.data.data
  if (r3.data.code === 200) exceptions.value = r3.data.data
  loading.value = false
}

const addRecord = async (status) => {
  try {
    const { value: location } = await ElMessageBox.prompt('请输入当前位置', '更新状态', { inputPlaceholder: '例如：广深高速K50' })
    const res = await transportRecordAPI.create({
      order_id: route.params.id,
      status,
      location,
      description: statusLabel(status)
    })
    if (res.data.code === 200) { ElMessage.success('更新成功'); loadData() }
    else ElMessage.error(res.data.message)
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

const viewFreight = async () => {
  const res = await orderAPI.getFreight(route.params.id)
  if (res.data.code === 200) {
    const f = res.data.data
    ElMessage.info(`计算运费: ¥${f.calculated_freight}（重量${f.weight}kg x ¥0.005 + 体积${f.volume}m³ x ¥100）`)
  }
}

const confirmPod = async () => {
  if (!podForm.signee_name) { ElMessage.warning('请输入签收人姓名'); return }
  try {
    const res = await orderAPI.confirmPod(route.params.id, podForm)
    if (res.data.code === 200) {
      ElMessage.success('POD签收确认成功')
      showPodDialog.value = false
      loadData()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) { ElMessage.error('操作失败') }
}

// 修改：打开完成订单对话框 
const completeOrder = () => {
  // 初始化表单，默认填入系统计算的运费
  completeForm.actual_freight = order.value?.freight_amount || null
  completeForm.remark = ''
  showCompleteDialog.value = true
}

// 新增：提交完成订单
const submitComplete = async () => {
  // 验证实际运费
  if (completeForm.actual_freight === null || completeForm.actual_freight === undefined) {
    ElMessage.warning('请输入实际运费')
    return
  }
  
  completing.value = true
  
  try {
    // 准备提交数据
    const submitData = {
      actual_freight: completeForm.actual_freight,
      remark: completeForm.remark
    }
  
    // 如果实际运费与系统计算的不一致，显示提示
    if (order.value && completeForm.actual_freight !== order.value.freight_amount) {
      const diff = completeForm.actual_freight - (order.value.freight_amount || 0)
      const diffText = diff > 0 ? `高出 ${diff} 元` : `低出 ${Math.abs(diff)} 元`
  
      await ElMessageBox.confirm(
        `实际运费与系统计算不一致，${diffText}。是否继续完成订单？`,
        '运费差异确认',
        {
          confirmButtonText: '继续完成',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
    }
  
    // 调用完成订单API，传入实际运费
    const res = await orderAPI.complete(route.params.id, submitData)
  
    if (res.data.code === 200) {
      ElMessage.success('订单已完成')
      showCompleteDialog.value = false
      loadData()  // 重新加载数据
    } else {
      ElMessage.error(res.data.message || '操作失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      console.error('完成订单失败:', e)
      ElMessage.error('操作失败')
    }
  } finally {
    completing.value = false
  }
}

// 异常相关函数
const createException = async () => {
  if (!exceptionForm.exception_type || !exceptionForm.description) {
    ElMessage.warning('请选择异常类型并填写描述')
    return
  }
  try {
    const res = await exceptionAPI.create({
      order_id: route.params.id,
      ...exceptionForm
    })
    if (res.data.code === 200) {
      ElMessage.success('异常登记成功')
      showExceptionDialog.value = false
      exceptionForm.exception_type = ''
      exceptionForm.severity = 'normal'
      exceptionForm.location = ''
      exceptionForm.description = ''
      exceptionForm.image = ''
      loadData()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) { ElMessage.error('操作失败') }
}

const openHandleDialog = (row) => {
  handleForm.id = row.id
  handleForm.handle_status = 'processing'
  handleForm.handle_note = ''
  showHandleDialog.value = true
}

const handleException = async () => {
  if (!handleForm.handle_status) {
    ElMessage.warning('请选择处理状态')
    return
  }
  try {
    const res = await exceptionAPI.update(handleForm.id, {
      handle_status: handleForm.handle_status,
      handle_note: handleForm.handle_note
    })
    if (res.data.code === 200) {
      ElMessage.success('异常处理状态已更新')
      showHandleDialog.value = false
      loadData()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) { ElMessage.error('操作失败') }
}

const deleteException = async (id) => {
  try {
    await ElMessageBox.confirm('确认删除该异常记录？', '删除确认', { type: 'warning' })
    const res = await exceptionAPI.delete(id)
    if (res.data.code === 200) {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
}

onMounted(() => { checkWidth(); window.addEventListener('resize', checkWidth); loadData() })
onUnmounted(() => { window.removeEventListener('resize', checkWidth) })
</script>
