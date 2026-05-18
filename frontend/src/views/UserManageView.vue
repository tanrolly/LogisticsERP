<template>
  <div class="user-manage-view">
    <div class="card-header">
      <h3>用户管理</h3>
      <el-button type="primary" @click="showCreateDialog">新增用户</el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索用户名/姓名"
        clearable
        style="width: 200px"
        @clear="fetchUsers"
        @keyup.enter="fetchUsers"
      />
      <el-select v-model="searchRole" placeholder="角色筛选" clearable style="width: 150px" @change="fetchUsers">
        <el-option v-for="r in roles" :key="r.code" :label="r.name" :value="r.code" />
      </el-select>
      <el-select v-model="searchStatus" placeholder="状态筛选" clearable style="width: 120px" @change="fetchUsers">
        <el-option label="启用" value="active" />
        <el-option label="禁用" value="inactive" />
      </el-select>
    </div>

    <!-- 用户列表 -->
    <el-table :data="users" stripe border style="width: 100%" v-loading="loading">
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="real_name" label="姓名" width="120" />
      <el-table-column prop="role_name" label="角色" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="getRoleTagType(row.role_code)">{{ row.role_name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="160" show-overflow-tooltip />
      <el-table-column prop="phone" label="电话" width="130" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'active' ? 'success' : 'danger'">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">
          {{ row.created_at ? row.created_at.replace('T', ' ').slice(0, 19) : '' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
          <el-button link type="warning" size="small" @click="handleResetPassword(row)">重置密码</el-button>
          <el-button
            v-if="row.status === 'active'"
            link type="danger" size="small"
            @click="handleToggleStatus(row)"
          >禁用</el-button>
          <el-button
            v-else
            link type="success" size="small"
            @click="handleToggleStatus(row)"
          >启用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchUsers"
      />
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="500px"
      destroy-on-close
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" :disabled="isEdit" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="formData.real_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="角色" prop="role_code">
          <el-select v-model="formData.role_code" placeholder="请选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.code" :label="r.name" :value="r.code" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="formData.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="formData.email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="formData.phone" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { userAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const roles = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const searchRole = ref('')
const searchStatus = ref('')

// 弹窗
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const editingUserId = ref(null)
const formData = ref({
  username: '',
  real_name: '',
  role_code: 'student',
  password: '',
  email: '',
  phone: ''
})
const formRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role_code: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

function getRoleTagType(code) {
  const map = {
    admin: 'danger',
    teacher: '',
    student: 'info',
    purchaser: 'success',
    customer_service: 'warning',
    dispatcher: '',
    warehouse_keeper: 'success',
    driver: 'info'
  }
  return map[code] || 'info'
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await userAPI.list({
      page: currentPage.value,
      per_page: pageSize.value,
      keyword: searchKeyword.value,
      role_code: searchRole.value,
      status: searchStatus.value
    })
    if (res.data.code === 200) {
      users.value = res.data.data.items
      total.value = res.data.data.total
    }
  } catch (err) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  try {
    const res = await userAPI.getRoles()
    if (res.data.code === 200) {
      roles.value = res.data.data
    }
  } catch {
    // fallback: 静默失败
  }
}

function showCreateDialog() {
  isEdit.value = false
  editingUserId.value = null
  formData.value = {
    username: '',
    real_name: '',
    role_code: 'student',
    password: '',
    email: '',
    phone: ''
  }
  dialogVisible.value = true
}

function showEditDialog(row) {
  isEdit.value = true
  editingUserId.value = row.id
  formData.value = {
    username: row.username,
    real_name: row.real_name,
    role_code: row.role_code,
    password: '',
    email: row.email || '',
    phone: row.phone || ''
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (isEdit.value) {
        const { password, ...updateData } = formData.value
        const res = await userAPI.update(editingUserId.value, updateData)
        if (res.data.code === 200) {
          ElMessage.success('用户信息已更新')
          dialogVisible.value = false
          fetchUsers()
        } else {
          ElMessage.error(res.data.message)
        }
      } else {
        const res = await userAPI.create(formData.value)
        if (res.data.code === 200) {
          ElMessage.success('用户创建成功')
          dialogVisible.value = false
          fetchUsers()
        } else {
          ElMessage.error(res.data.message)
        }
      }
    } catch (err) {
      ElMessage.error(err.response?.data?.message || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

async function handleResetPassword(row) {
  let value
  try {
    const { value: pwd } = await ElMessageBox.prompt('请输入新密码', '重置密码', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputType: 'password',
      inputPattern: /.{4,}/,
      inputErrorMessage: '密码至少4个字符'
    })
    value = pwd
  } catch {
    return // 用户取消
  }

  if (!value) return

  try {
    const res = await userAPI.resetPassword(row.id, value)
    if (res.data.code === 200) {
      ElMessage.success(`用户 ${row.real_name} 的密码已重置`)
    }
  } catch (err) {
    ElMessage.error('重置密码失败')
  }
}

async function handleToggleStatus(row) {
  const action = row.status === 'active' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${action}用户 ${row.real_name} 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

  try {
    const res = await userAPI.update(row.id, { status: row.status === 'active' ? 'inactive' : 'active' })
    if (res.data.code === 200) {
      ElMessage.success(`用户已${action}`)
      fetchUsers()
    }
  } catch (err) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  fetchRoles()
  fetchUsers()
})
</script>

<style scoped>
.user-manage-view {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-header h3 {
  margin: 0;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .search-bar {
    flex-direction: column;
  }

  .search-bar .el-input,
  .search-bar .el-select {
    width: 100% !important;
  }
}
</style>
