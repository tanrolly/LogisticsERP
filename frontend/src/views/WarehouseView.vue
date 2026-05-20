<template>
  <div class="warehouse-view">
    <PageGuide v-bind="guideConfig" />
<!-- 仓库列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>仓库管理</span>
          <el-button type="primary" @click="showWarehouseDialog('add')">新增仓库</el-button>
        </div>
      </template>

      <el-table :data="warehouseList" style="width: 100%" highlight-current-row
                @current-change="handleWarehouseSelect">
        <el-table-column prop="name" label="仓库名称" />
        <el-table-column prop="address" label="地址" />
        <el-table-column label="类型" width="100">
          <template #default="scope">
            <el-tag size="small" :type="scope.row.type === 'cold' ? 'primary' : scope.row.type === 'dangerous' ? 'danger' : 'info'">
              {{ typeLabel(scope.row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_locations" label="总货位数" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="showWarehouseDialog('edit', scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeleteWarehouse(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 库区列表 -->
    <el-card v-if="selectedWarehouseId" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>库区管理 — {{ selectedWarehouseName }}</span>
          <el-button type="primary" size="small" @click="showZoneDialog('add')">新增库区</el-button>
        </div>
      </template>

      <el-table :data="zoneList" style="width: 100%" highlight-current-row
                @current-change="handleZoneSelect">
        <el-table-column prop="zone_code" label="库区编码" width="120" />
        <el-table-column prop="zone_name" label="库区名称" />
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="showZoneDialog('edit', scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeleteZone(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 货位列表 -->
    <el-card v-if="selectedZoneId" style="margin-top: 16px">
      <template #header>
        <div class="card-header">
          <span>货位管理 — {{ selectedZoneName }}</span>
          <el-button type="primary" size="small" @click="showLocationDialog('add')">新增货位</el-button>
        </div>
      </template>

      <el-table :data="locationList" style="width: 100%">
        <el-table-column prop="loc_code" label="货位编码" width="120" />
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
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="locStatusType(scope.row.status)" size="small">
              {{ locStatusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="showLocationDialog('edit', scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeleteLocation(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 仓库对话框 -->
    <el-dialog v-model="warehouseDialogVisible" :title="warehouseDialogType === 'add' ? '新增仓库' : '编辑仓库'" width="480px">
      <el-form :model="warehouseForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="warehouseForm.name" placeholder="请输入仓库名称" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="warehouseForm.address" type="textarea" placeholder="请输入仓库地址" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="warehouseForm.type" placeholder="请选择仓库类型">
            <el-option label="普通仓库" value="normal" />
            <el-option label="冷藏仓库" value="cold" />
            <el-option label="危险品仓库" value="dangerous" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="warehouseDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveWarehouse">确定</el-button>
      </template>
    </el-dialog>

    <!-- 库区对话框 -->
    <el-dialog v-model="zoneDialogVisible" :title="zoneDialogType === 'add' ? '新增库区' : '编辑库区'" width="480px">
      <el-form :model="zoneForm" label-width="80px">
        <el-form-item label="库区编码" required>
          <el-input v-model="zoneForm.zone_code" placeholder="如：A" />
        </el-form-item>
        <el-form-item label="库区名称" required>
          <el-input v-model="zoneForm.zone_name" placeholder="如：A区-常温区" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="zoneForm.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="zoneDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveZone">确定</el-button>
      </template>
    </el-dialog>

    <!-- 货位对话框 -->
    <el-dialog v-model="locationDialogVisible" :title="locationDialogType === 'add' ? '新增货位' : '编辑货位'" width="480px">
      <el-form :model="locationForm" label-width="90px">
        <el-form-item label="货位编码" required>
          <el-input v-model="locationForm.loc_code" placeholder="如：A-01-01" />
        </el-form-item>
        <el-form-item label="载重(吨)">
          <el-input-number v-model="locationForm.capacity_weight" :min="0" :precision="1" :step="0.5" />
        </el-form-item>
        <el-form-item label="容积(立方米)">
          <el-input-number v-model="locationForm.capacity_volume" :min="0" :precision="1" :step="1" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="locationForm.status" placeholder="请选择">
            <el-option label="空闲" value="empty" />
            <el-option label="占用" value="occupied" />
            <el-option label="已满" value="full" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="locationDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveLocation">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import PageGuide from '../components/PageGuide.vue'

const guideConfig = { title: '仓库管理操作指引', steps: [
        "先创建仓库",
        "再在仓库下创建库区",
        "最后在库区下创建货位"
    ], tips: [
        "必须按层级创建：仓库→库区→货位",
        "点击仓库可打开库区管理页面",
        "点击库区可打开货位管理页面",
        "删除上级会级联删除下级"
    ] }
import { ref, onMounted, onUnmounted } from 'vue'
import { warehouseAPI } from '../api/common'
import { ElMessage, ElMessageBox } from 'element-plus'

// === 数据 ===
const warehouseList = ref([])
const zoneList = ref([])
const locationList = ref([])
const selectedWarehouseId = ref(null)
const selectedWarehouseName = ref('')
const selectedZoneId = ref(null)
const selectedZoneName = ref('')

// === 仓库对话框 ===
const warehouseDialogVisible = ref(false)
const warehouseDialogType = ref('add')
const warehouseCurrentId = ref(null)
const defaultWarehouseForm = { name: '', address: '', type: 'normal' }
const warehouseForm = ref({ ...defaultWarehouseForm })

// === 库区对话框 ===
const zoneDialogVisible = ref(false)
const zoneDialogType = ref('add')
const zoneCurrentId = ref(null)
const defaultZoneForm = { zone_code: '', zone_name: '', sort_order: 0 }
const zoneForm = ref({ ...defaultZoneForm })

// === 货位对话框 ===
const locationDialogVisible = ref(false)
const locationDialogType = ref('add')
const locationCurrentId = ref(null)
const defaultLocationForm = { loc_code: '', capacity_weight: null, capacity_volume: null, status: 'empty' }
const locationForm = ref({ ...defaultLocationForm })

// === 工具函数 ===
const typeLabel = (type) => ({ normal: '普通', cold: '冷藏', dangerous: '危险品' })[type] || type
const locStatusLabel = (s) => ({ empty: '空闲', occupied: '占用', full: '已满' })[s] || s
const locStatusType = (s) => ({ empty: 'success', occupied: 'warning', full: 'danger' })[s] || 'info'

const isMobile = ref(false)
const checkWidth = () => { isMobile.value = window.innerWidth < 768 }

// === 仓库操作 ===
const loadWarehouses = async () => {
  try {
    const res = await warehouseAPI.list()
    if (res.data.code === 200) {
      warehouseList.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载仓库列表失败')
  }
}

const handleWarehouseSelect = (row) => {
  if (!row) return
  selectedWarehouseId.value = row.id
  selectedWarehouseName.value = row.name
  selectedZoneId.value = null
  zoneList.value = []
  locationList.value = []
  loadZones(row.id)
}

const showWarehouseDialog = (type, row) => {
  warehouseDialogType.value = type
  if (type === 'add') {
    warehouseForm.value = { ...defaultWarehouseForm }
  } else {
    warehouseCurrentId.value = row.id
    warehouseForm.value = { name: row.name, address: row.address, type: row.type }
  }
  warehouseDialogVisible.value = true
}

const handleSaveWarehouse = async () => {
  if (!warehouseForm.value.name) {
    ElMessage.warning('仓库名称不能为空')
    return
  }
  try {
    let res
    if (warehouseDialogType.value === 'add') {
      res = await warehouseAPI.create(warehouseForm.value)
    } else {
      res = await warehouseAPI.update(warehouseCurrentId.value, warehouseForm.value)
    }
    if (res.data.code === 200) {
      ElMessage.success('保存成功')
      warehouseDialogVisible.value = false
      loadWarehouses()
    } else {
      ElMessage.error(res.data.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const handleDeleteWarehouse = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该仓库吗？删除前需先清空其下所有库区。', '提示', { type: 'warning' })
    const res = await warehouseAPI.delete(row.id)
    if (res.data.code === 200) {
      ElMessage.success('删除成功')
      if (selectedWarehouseId.value === row.id) {
        selectedWarehouseId.value = null
        zoneList.value = []
        locationList.value = []
      }
      loadWarehouses()
    } else {
      ElMessage.error(res.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// === 库区操作 ===
const loadZones = async (warehouseId) => {
  try {
    const res = await warehouseAPI.getZones(warehouseId)
    if (res.data.code === 200) {
      zoneList.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载库区列表失败')
  }
}

const handleZoneSelect = (row) => {
  if (!row) return
  selectedZoneId.value = row.id
  selectedZoneName.value = row.zone_name
  locationList.value = []
  loadLocations(row.id)
}

const showZoneDialog = (type, row) => {
  zoneDialogType.value = type
  if (type === 'add') {
    zoneForm.value = { ...defaultZoneForm }
  } else {
    zoneCurrentId.value = row.id
    zoneForm.value = { zone_code: row.zone_code, zone_name: row.zone_name, sort_order: row.sort_order }
  }
  zoneDialogVisible.value = true
}

const handleSaveZone = async () => {
  if (!zoneForm.value.zone_code || !zoneForm.value.zone_name) {
    ElMessage.warning('库区编码和名称不能为空')
    return
  }
  try {
    let res
    if (zoneDialogType.value === 'add') {
      res = await warehouseAPI.createZone({ ...zoneForm.value, warehouse_id: selectedWarehouseId.value })
    } else {
      res = await warehouseAPI.updateZone(zoneCurrentId.value, zoneForm.value)
    }
    if (res.data.code === 200) {
      ElMessage.success('保存成功')
      zoneDialogVisible.value = false
      loadZones(selectedWarehouseId.value)
      loadWarehouses() // 刷新仓库货位数
    } else {
      ElMessage.error(res.data.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const handleDeleteZone = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该库区吗？删除前需先清空其下所有货位。', '提示', { type: 'warning' })
    const res = await warehouseAPI.deleteZone(row.id)
    if (res.data.code === 200) {
      ElMessage.success('删除成功')
      if (selectedZoneId.value === row.id) {
        selectedZoneId.value = null
        locationList.value = []
      }
      loadZones(selectedWarehouseId.value)
      loadWarehouses()
    } else {
      ElMessage.error(res.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// === 货位操作 ===
const loadLocations = async (zoneId) => {
  try {
    const res = await warehouseAPI.getLocations(zoneId)
    if (res.data.code === 200) {
      locationList.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载货位列表失败')
  }
}

const showLocationDialog = (type, row) => {
  locationDialogType.value = type
  if (type === 'add') {
    locationForm.value = { ...defaultLocationForm }
  } else {
    locationCurrentId.value = row.id
    locationForm.value = {
      loc_code: row.loc_code,
      capacity_weight: row.capacity_weight,
      capacity_volume: row.capacity_volume,
      status: row.status
    }
  }
  locationDialogVisible.value = true
}

const handleSaveLocation = async () => {
  if (!locationForm.value.loc_code) {
    ElMessage.warning('货位编码不能为空')
    return
  }
  try {
    let res
    if (locationDialogType.value === 'add') {
      res = await warehouseAPI.createLocation({ ...locationForm.value, zone_id: selectedZoneId.value })
    } else {
      res = await warehouseAPI.updateLocation(locationCurrentId.value, locationForm.value)
    }
    if (res.data.code === 200) {
      ElMessage.success('保存成功')
      locationDialogVisible.value = false
      loadLocations(selectedZoneId.value)
      loadWarehouses()
    } else {
      ElMessage.error(res.data.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const handleDeleteLocation = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该货位吗？已占用的货位无法删除。', '提示', { type: 'warning' })
    const res = await warehouseAPI.deleteLocation(row.id)
    if (res.data.code === 200) {
      ElMessage.success('删除成功')
      loadLocations(selectedZoneId.value)
      loadWarehouses()
    } else {
      ElMessage.error(res.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// === 初始化 ===
onMounted(() => {
  checkWidth()
  window.addEventListener('resize', checkWidth)
  loadWarehouses()
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
