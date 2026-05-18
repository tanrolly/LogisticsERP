import axios from 'axios'

/**
 * 采购合同 API
 */
export const purchaseContractAPI = {
  getList: (params) => axios.get('/contracts/purchase', { params }),
  getEligibleOrders: () => axios.get('/contracts/purchase/eligible'),
  create: (data) => axios.post('/contracts/purchase', data),
  getDetail: (id) => axios.get(`/contracts/purchase/${id}`),
  approve: (id, data) => axios.put(`/contracts/purchase/${id}/approve`, data),
  reject: (id, data) => axios.put(`/contracts/purchase/${id}/reject`, data),
  return: (id, data) => axios.put(`/contracts/purchase/${id}/return`, data),
  terminate: (id) => axios.put(`/contracts/purchase/${id}/terminate`)
}

/**
 * 运输合同 API
 */
export const transportContractAPI = {
  getList: (params) => axios.get('/contracts/transport', { params }),
  getEligibleOrders: () => axios.get('/contracts/transport/eligible'),
  create: (data) => axios.post('/contracts/transport', data),
  getDetail: (id) => axios.get(`/contracts/transport/${id}`),
  approve: (id, data) => axios.put(`/contracts/transport/${id}/approve`, data),
  reject: (id, data) => axios.put(`/contracts/transport/${id}/reject`, data),
  return: (id, data) => axios.put(`/contracts/transport/${id}/return`, data),
  terminate: (id) => axios.put(`/contracts/transport/${id}/terminate`)
}

/**
 * 合同概览统计 API
 */
export const contractOverviewAPI = {
  getOverview: () => axios.get('/contracts/overview')
}
