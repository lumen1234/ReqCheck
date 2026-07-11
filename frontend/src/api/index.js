import axios from 'axios'
import { getPortalProjectId } from '../utils/portal'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: '/api',  // Vite 代理会将 /api 转发到后端
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：UniPortal 工程隔离 — 所有 GET 自动附带 portal_project_id
apiClient.interceptors.request.use(
  config => {
    const portalProjectId = getPortalProjectId()
    if (portalProjectId && (config.method || 'get').toLowerCase() === 'get') {
      config.params = { ...(config.params || {}), portal_project_id: portalProjectId }
    }
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器（保留原错误处理）
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error.response?.data || error.message)
    // 可以在这里统一处理错误
    if (error.response?.status === 401) {
      // 未授权处理
    } else if (error.response?.status === 500) {
      // 服务器错误处理
    }
    return Promise.reject(error)
  }
)

// ==================== API 方法封装 ====================
// 说明：所有接口统一使用 docId（文档ID）作为唯一标识
// 上传后获得 docId，后续所有操作都基于这个 docId 进行

/**
 * 上传文档
 * @param {FormData} formData - 包含文档文件和元数据的表单数据
 * @returns {Promise} 返回文档ID和名称 { doc_id, doc_name }
 */
export const uploadDocument = (formData) => {
  return apiClient.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/**
 * 获取文档列表（支持 UniPortal 工程隔离）
 * @param {string|null} portalProjectId - 可选，UniPortal 工程 UUID
 */
export const getDocuments = (portalProjectId = getPortalProjectId()) => {
  const params = portalProjectId ? { portal_project_id: portalProjectId } : {}
  return apiClient.get('/documents', { params })
}

/**
 * 获取文档详情
 * @param {string} docId - 文档ID
 * @returns {Promise} 返回文档详细信息
 */
export const getDocumentDetail = (docId) => {
  return apiClient.get(`/documents/${docId}`)
}

/**
 * 获取解析结果（需求树）
 * @param {string} docId - 文档ID
 * @returns {Promise} 返回解析后的需求树结构
 */
export const getParseResult = (docId, options = {}) => {
  const portalProjectId = options.portalProjectId ?? getPortalProjectId()
  const params = { ...(options.force ? { force: '1' } : {}) }
  if (portalProjectId) {
    params.portal_project_id = portalProjectId
  }
  return apiClient.get(`/parse/${docId}`, { params })
}

/**
 * 获取验证结果
 * @param {string} docId - 文档ID
 * @returns {Promise} 返回验证结果 { validation_results: [...] }
 */
export const getReviewResult = (docId, params = {}) => {
  return apiClient.get(`/validate/${docId}`, { params })
}

/**
 * 导出需求树（JSON格式）
 * @param {string} docId - 文档ID
 * @returns {Promise} 返回扁平化的需求列表 { requirements: [...], total_requirements: number }
 */
export const exportRequirements = (docId, portalProjectId = getPortalProjectId()) => {
  const params = portalProjectId ? { portal_project_id: portalProjectId } : {}
  return apiClient.get(`/export/${docId}`, { params })
}

/**
 * 删除文档
 * @param {string} docId - 文档ID
 * @returns {Promise} 返回删除结果 { success: true, doc_id, deleted_files, errors }
 */
export const deleteDocument = (docId) => {
  return apiClient.delete(`/delete/${docId}`)
}

// ==================== LLM 配置接口 ====================

/**
 * 获取当前 LLM 配置
 * @returns {Promise} 返回 LLM 配置 { api_key, base_url, model }
 */
export const getLLMConfig = () => {
  return apiClient.get('/config/llm')
}

/**
 * 保存 LLM 配置
 * @param {{ api_key: string, base_url: string, model: string }} payload - LLM 配置
 * @returns {Promise} 返回保存结果 { success: true }
 */
export const saveLLMConfig = (payload) => {
  return apiClient.put('/config/llm', payload)
}

/**
 * 测试 LLM 连接
 * @returns {Promise} 返回测试结果 { ok: boolean, model: string, reply?: string, error?: string }
 */
export const testLLMConnection = () => {
  return apiClient.post('/config/llm/test')
}


export const uploadFolder = (formData) => {
 return apiClient.post('/upload/folder', formData, {
 headers: { 'Content-Type': 'multipart/form-data' }
 })
}

export const getBatchDetail = (batchId) => {
 return apiClient.get(`/batches/${batchId}`)
}

export const exportBatchRequirements = (batchId, portalProjectId = getPortalProjectId()) => {
 const params = portalProjectId ? { portal_project_id: portalProjectId } : {}
 return apiClient.get(`/export/batch/${batchId}`, { params })
}

export default apiClient
