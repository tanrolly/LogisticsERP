import axios from 'axios'

// 通用CRUD工厂函数
function crudApi(path) {
  return {
    list: (params) => axios.get(`/${path}`, { params }),
    get: (id) => axios.get(`/${path}/${id}`),
    create: (data) => axios.post(`/${path}`, data),
    update: (id, data) => axios.put(`/${path}/${id}`, data),
    delete: (id) => axios.delete(`/${path}/${id}`),
    action: (id, action, data) => axios.put(`/${path}/${id}/${action}`, data)
  }
}

export const supplierAPI = crudApi('suppliers')
export const customerAPI = crudApi('customers')
export const vehicleAPI = crudApi('vehicles')
export const driverAPI = crudApi('drivers')
export const goodsAPI = crudApi('goods')

// 采购管理
export const purchaseRequestAPI = {
  ...crudApi('purchase-requests'),
  approve: (id, comment) => axios.put(`/purchase-requests/${id}/approve`, { comment }),
  reject: (id, comment) => axios.put(`/purchase-requests/${id}/reject`, { comment }),
  return: (id, comment) => axios.put(`/purchase-requests/${id}/return`, { comment }),
  resubmit: (id) => axios.put(`/purchase-requests/${id}/resubmit`)
}

export const purchaseOrderAPI = {
  ...crudApi('purchase-orders'),
  confirm: (id) => axios.put(`/purchase-orders/${id}/confirm`),
  updateStatus: (id, status) => axios.put(`/purchase-orders/${id}/status`, { status })
}

export const purchaseReceiptAPI = {
  list: (params) => axios.get('/purchase-receipts', { params }),
  create: (data) => axios.post('/purchase-receipts', data)
}

// 运输管理
export const orderAPI = {
  list: (params) => axios.get('/orders', { params }),
  get: (id) => axios.get(`/orders/${id}`),
  create: (data) => axios.post('/orders', data),
  approve: (id) => axios.put(`/orders/${id}/approve`),
  reject: (id, comment) => axios.put(`/orders/${id}/reject`, { comment }),
  return: (id, comment) => axios.put(`/orders/${id}/return`, { comment }),
  resubmit: (id) => axios.put(`/orders/${id}/resubmit`),
  dispatch: (id, data) => axios.put(`/orders/${id}/dispatch`, data),
  updateStatus: (id, data) => axios.put(`/orders/${id}/status`, data),
  getFreight: (id) => axios.get(`/orders/${id}/freight`),
  confirmPod: (id, data) => axios.post(`/orders/${id}/pod`, data),
  complete: (id, data) => axios.put(`/orders/${id}/complete`, data)
}

export const transportRecordAPI = {
  list: (params) => axios.get('/transport-records', { params }),
  create: (data) => axios.post('/transport-records', data)
}

export const exceptionAPI = {
  list: (params) => axios.get('/exceptions', { params }),
  get: (id) => axios.get(`/exceptions/${id}`),
  create: (data) => axios.post('/exceptions', data),
  update: (id, data) => axios.put(`/exceptions/${id}`, data),
  delete: (id) => axios.delete(`/exceptions/${id}`)
}

// 仓库/库区/货位
export const warehouseAPI = {
  ...crudApi('warehouses'),
  getZones: (warehouseId) => axios.get(`/warehouses/${warehouseId}/zones`),
  createZone: (data) => axios.post('/zones', data),
  getLocations: (zoneId) => axios.get(`/zones/${zoneId}/locations`),
  createLocation: (data) => axios.post('/locations', data)
}

// 入库管理
export const inboundAPI = {
  list: (params) => axios.get('/inbound', { params }),
  get: (id) => axios.get(`/inbound/${id}`),
  create: (data) => axios.post('/inbound', data),
  shelve: (id, data) => axios.post(`/inbound/${id}/shelve`, data)
}

// 出库管理
export const outboundAPI = {
  list: (params) => axios.get('/outbound', { params }),
  get: (id) => axios.get(`/outbound/${id}`),
  create: (data) => axios.post('/outbound', data),
  pick: (id, data) => axios.post(`/outbound/${id}/pick`, data),
  ship: (id) => axios.post(`/outbound/${id}/ship`)
}

// 库存管理
export const inventoryAPI = {
  list: (params) => axios.get('/inventory', { params }),
  get: (id) => axios.get(`/inventory/${id}`),
  getSummary: (params) => axios.get('/inventory/summary', { params }),
  getAlerts: () => axios.get('/inventory/alerts')
}

// 库存移动
export const stockMoveAPI = {
  list: (params) => axios.get('/stock-moves', { params })
}

// 库存盘点
export const stockCountAPI = {
  list: (params) => axios.get('/stock-counts', { params }),
  get: (id) => axios.get(`/stock-counts/${id}`),
  create: (data) => axios.post('/stock-counts', data),
  count: (id, data) => axios.post(`/stock-counts/${id}/count`, data),
  reconcile: (id) => axios.post(`/stock-counts/${id}/reconcile`)
}

// ============ 协作房间 ============
export const roomAPI = {
  list: (params) => axios.get('/rooms', { params }),
  get: (id) => axios.get(`/rooms/${id}`),
  create: (data) => axios.post('/rooms', data),
  join: (id, data) => axios.post(`/rooms/${id}/join`, data),
  leave: (id) => axios.post(`/rooms/${id}/leave`),
  close: (id) => axios.post(`/rooms/${id}/close`),
  getProgress: (id) => axios.get(`/rooms/${id}/progress`)
}

// ============ 教学场景 ============
export const sceneAPI = {
  list: () => axios.get('/scenes'),
  get: (id) => axios.get(`/scenes/${id}`),
  create: (data) => axios.post('/scenes', data),
  update: (id, data) => axios.put(`/scenes/${id}`, data),
  delete: (id) => axios.delete(`/scenes/${id}`)
}

// ============ 突发事件 ============
export const eventAPI = {
  inject: (data) => axios.post('/events/inject', data),
  getTypes: () => axios.get('/events/types')
}

// ============ 操作日志 ============
export const logAPI = {
  list: (params) => axios.get('/operation-logs', { params }),
  getStats: (params) => axios.get('/operation-logs/stats', { params }),
  replay: (params) => axios.get('/operation-logs/replay', { params }),
  getDetail: (id) => axios.get(`/operation-logs/${id}`)
}

// ============ 评分 ============
export const scoreAPI = {
  getGroupScore: (groupId) => axios.get(`/scores/group/${groupId}`),
  getUserScore: (userId, params) => axios.get(`/scores/user/${userId}`, { params }),
  getRanking: (params) => axios.get('/scores/ranking', { params }),
  getGroupRanking: () => axios.get('/scores/group-ranking'),
  getAll: (params) => axios.get('/scores/all', { params })
}

// ============ 角色 ============
export const roleAPI = {
  list: () => axios.get('/roles')
}

// ============ 用户管理 ============
export const userAPI = {
  list: (params) => axios.get('/users', { params }),
  get: (id) => axios.get(`/users/${id}`),
  create: (data) => axios.post('/users', data),
  update: (id, data) => axios.put(`/users/${id}`, data),
  delete: (id) => axios.delete(`/users/${id}`),
  resetPassword: (id, password) => axios.put(`/users/${id}/reset-password`, { password }),
  getRoles: () => axios.get('/users/roles')
}

// ============ 审批记录 ============
export const approvalAPI = {
  list: (params) => axios.get('/approval-records', { params }),
  get: (id) => axios.get(`/approval-records/${id}`)
}
