<template>
  <div class="contract-detail-view">
    <el-page-header @back="goBack" :content="pageTitle" />

    <div v-loading="loading" class="detail-content">
      <template v-if="contract">
        <!-- 采购合同详情 -->
        <template v-if="contractType === 'purchase'">
          <el-descriptions :column="3" border class="detail-section">
            <el-descriptions-item label="合同编号">{{ contract.contract_no }}</el-descriptions-item>
            <el-descriptions-item label="关联采购订单">{{ contract.po_no }}</el-descriptions-item>
            <el-descriptions-item label="供应商">{{ contract.supplier_name }}</el-descriptions-item>
            <el-descriptions-item label="合同金额">
              <span style="color: #e6a23c; font-weight: bold;">¥{{ contract.total_amount?.toFixed(2) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusType(contract.status)">{{ statusText(contract.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="操作人">{{ contract.operator_name }}</el-descriptions-item>
            <el-descriptions-item label="签订日期">{{ contract.sign_date }}</el-descriptions-item>
            <el-descriptions-item label="生效日期">{{ contract.start_date }}</el-descriptions-item>
            <el-descriptions-item label="终止日期">{{ contract.end_date }}</el-descriptions-item>
          </el-descriptions>

          <el-descriptions :column="1" border class="detail-section" title="条款信息">
            <el-descriptions-item label="付款条款">{{ contract.payment_terms || '未填写' }}</el-descriptions-item>
            <el-descriptions-item label="交货条款">{{ contract.delivery_terms || '未填写' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 审批信息 -->
          <el-descriptions :column="2" border class="detail-section" title="审批信息">
            <el-descriptions-item label="审批人">{{ contract.reviewer_name || '未审批' }}</el-descriptions-item>
            <el-descriptions-item label="审批时间">{{ contract.reviewed_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="审批意见" :span="2">{{ contract.review_comment || '-' }}</el-descriptions-item>
          </el-descriptions>
        </template>

        <!-- 运输合同详情 -->
        <template v-if="contractType === 'transport'">
          <el-descriptions :column="3" border class="detail-section">
            <el-descriptions-item label="合同编号">{{ contract.contract_no }}</el-descriptions-item>
            <el-descriptions-item label="关联运输订单">{{ contract.order_no }}</el-descriptions-item>
            <el-descriptions-item label="客户">{{ contract.customer_name }}</el-descriptions-item>
            <el-descriptions-item label="运费金额">
              <span style="color: #e6a23c; font-weight: bold;">¥{{ contract.freight_amount?.toFixed(2) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusType(contract.status)">{{ statusText(contract.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="操作人">{{ contract.operator_name }}</el-descriptions-item>
            <el-descriptions-item label="签订日期">{{ contract.sign_date }}</el-descriptions-item>
            <el-descriptions-item label="生效日期">{{ contract.start_date }}</el-descriptions-item>
            <el-descriptions-item label="终止日期">{{ contract.end_date }}</el-descriptions-item>
          </el-descriptions>

          <el-descriptions :column="1" border class="detail-section" title="条款信息">
            <el-descriptions-item label="付款条款">{{ contract.payment_terms || '未填写' }}</el-descriptions-item>
            <el-descriptions-item label="运输条款">{{ contract.transport_terms || '未填写' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 审批信息 -->
          <el-descriptions :column="2" border class="detail-section" title="审批信息">
            <el-descriptions-item label="审批人">{{ contract.reviewer_name || '未审批' }}</el-descriptions-item>
            <el-descriptions-item label="审批时间">{{ contract.reviewed_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="审批意见" :span="2">{{ contract.review_comment || '-' }}</el-descriptions-item>
          </el-descriptions>
        </template>

        <!-- 时间信息 -->
        <el-descriptions :column="2" border class="detail-section" title="时间记录">
          <el-descriptions-item label="创建时间">{{ contract.created_at }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ contract.updated_at }}</el-descriptions-item>
        </el-descriptions>

        <!-- 审批记录 -->
        <el-card class="detail-section">
          <template #header><span>审批记录</span></template>
          <ApprovalTimeline :target-type="contractType === 'purchase' ? 'purchase_contract' : 'transport_contract'" :target-id="contract.id" />
        </el-card>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { purchaseContractAPI, transportContractAPI } from '../../api/contract'
import ApprovalTimeline from '../../components/ApprovalTimeline.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const contract = ref(null)

const contractType = computed(() => route.params.type)
const contractId = computed(() => route.params.id)
const pageTitle = computed(() => {
  if (contractType.value === 'purchase') return '采购合同详情'
  return '运输合同详情'
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

const loadDetail = async () => {
  loading.value = true
  try {
    const type = contractType.value
    const id = contractId.value
    let res
    if (type === 'purchase') {
      res = await purchaseContractAPI.getDetail(id)
    } else {
      res = await transportContractAPI.getDetail(id)
    }
    if (res.data.code === 200) {
      contract.value = res.data.data
    }
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  if (contractType.value === 'purchase') {
    router.push('/contract/purchase')
  } else {
    router.push('/contract/transport')
  }
}

onMounted(() => {
  loadDetail()
})
</script>

<style scoped>
.contract-detail-view { padding: 20px; }
.detail-content { margin-top: 20px; }
.detail-section { margin-bottom: 20px; }
</style>
