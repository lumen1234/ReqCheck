import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000 // 增加超时时间到120秒
})

// 上传文档
export const uploadDocument = (file, fileType) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('file_type', fileType)
  return api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 解析文档
export const parseDocument = (docId) => {
  return api.post('/parse', { doc_id: docId })
}

// 验证需求
export const validateRequirements = (docId) => {
  return api.post('/validate', { doc_id: docId })
}

// 导出需求
export const exportRequirements = (docId) => {
  return api.post('/export', { doc_id: docId })
}

// 获取文档列表
export const getDocuments = () => {
  return api.get('/documents')
}

// 获取文档详情
export const getDocumentDetail = (docId) => {
  return api.get(`/document/${docId}`)
}

export default api
