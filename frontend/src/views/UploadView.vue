<template>
  <div class="h-full overflow-y-auto p-8 bg-white">
    <div class="max-w-4xl mx-auto space-y-8">
      <!-- Header -->
      <div class="text-center space-y-2">
        <h1 class="text-3xl font-bold text-slate-900">欢迎使用文档审查系统</h1>
        <p class="text-slate-500 font-medium">上传您的文档以开始自动化审查分析</p>
      </div>

      <!-- Upload Card -->
      <div class="bg-slate-50 border border-slate-200 rounded-xl p-8 shadow-sm">
        <div v-if="!selectedFile"
          class="border-2 border-dashed border-slate-300 rounded-lg p-12 text-center hover:border-primary-600 transition-colors cursor-pointer group bg-white"
          @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
          <input type="file" ref="fileInput" class="hidden" @change="handleFileChange" accept=".pdf,.doc,.docx,.txt" />
          <div class="flex flex-col items-center space-y-4">
            <div
              class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center group-hover:bg-primary-50 transition-colors">
              <Upload class="w-8 h-8 text-slate-400 group-hover:text-primary-600" />
            </div>
            <div class="space-y-1">
              <p class="text-lg font-bold text-slate-700">点击或拖拽文件至此处上传</p>
              <p class="text-sm text-slate-500">支持 .pdf, .doc, .docx, .txt 等文档格式</p>
            </div>
          </div>
        </div>

        <!-- File Selected State -->
        <div v-else class="space-y-6">
          <div class="flex items-center justify-between p-4 bg-white border border-slate-200 rounded-lg">
            <div class="flex items-center space-x-4">
              <div class="w-12 h-12 bg-primary-50 rounded flex items-center justify-center">
                <FileText class="w-7 h-7 text-primary-600" />
              </div>
              <div>
                <p class="text-sm font-bold text-slate-700">{{ selectedFile.name }}</p>
                <p class="text-xs text-slate-500">{{ (selectedFile.size / 1024).toFixed(2) }} KB</p>
              </div>
            </div>
            <button @click="cancelSelection" class="text-slate-400 hover:text-red-500 transition-colors"
              v-if="!uploading">
              <X class="w-5 h-5" />
            </button>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-bold text-slate-700">文档名称</label>
            <input v-model="documentName" type="text"
              class="w-full px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              placeholder="请输入文档名称" :disabled="uploading" />
          </div>

          <button @click="uploadFile" :disabled="uploading || !documentName.trim()"
            class="w-full py-3 bg-primary-900 hover:bg-primary-800 disabled:bg-slate-300 text-white font-bold rounded-lg transition-all shadow-md flex items-center justify-center space-x-2">
            <Upload class="w-5 h-5" v-if="!uploading" />
            <RotateCw class="w-5 h-5 animate-spin" v-else />
            <span>{{ uploading ? '正在上传...' : '确认上传并开始审查' }}</span>
          </button>
        </div>

        <!-- Upload Progress -->
        <div v-if="uploading" class="mt-6 space-y-2">
          <div class="flex justify-between text-sm mb-1 font-medium text-slate-600">
            <span>正在上传文档...</span>
            <span>{{ uploadProgress }}%</span>
          </div>
          <div class="w-full bg-slate-200 rounded-full h-2">
            <div class="bg-primary-600 h-2 rounded-full transition-all duration-300"
              :style="{ width: uploadProgress + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Document List Section -->
      <div class="space-y-4">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2">
          <h2 class="text-xl font-bold flex items-center gap-2 text-slate-800">
            <History class="w-5 h-5 text-primary-600" />
            {{ portalProjectId ? '项目列表（UniPortal + 本地上传）' : '历史文档（本地上传）' }}
          </h2>
          <button @click="fetchDocuments" class="text-sm font-semibold text-primary-600 hover:text-primary-700">
            刷新列表
          </button>
        </div>

        <div v-if="loading" class="text-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
        </div>

        <div v-else-if="documents.length === 0" class="bg-slate-50 border border-slate-200 rounded-lg p-12 text-center">
          <p class="text-slate-400 font-medium">暂无文档，请先上传一个</p>
        </div>

        <div v-else class="grid grid-cols-1 gap-4">
          <div v-for="doc in documents" :key="doc.id"
            class="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-all cursor-pointer group"
            @click="selectDocument(doc)">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-4">
                <div class="w-10 h-10 bg-primary-50 rounded flex items-center justify-center">
                  <FileText class="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <p class="text-sm font-bold text-slate-900">{{ doc.filename }}</p>
                    <span
                      v-if="doc.source === 'uniportal'"
                      class="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-blue-100 text-blue-800"
                    >UniPortal</span>
                    <span
                      v-else-if="doc.source === 'local'"
                      class="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-slate-100 text-slate-600"
                    >本地</span>
                  </div>
                  <p class="text-xs text-slate-500">{{ doc.upload_time }}</p>
                </div>
              </div>
              <div class="flex items-center space-x-2">
                <button
                  v-if="doc.source !== 'uniportal'"
                  @click="handleDeleteDocument(doc, $event)"
                  :disabled="deleting && deletingDocId === doc.id"
                  class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-all disabled:opacity-50"
                  title="删除文档">
                  <Trash2 class="w-4 h-4" :class="{ 'animate-pulse': deleting && deletingDocId === doc.id }" />
                </button>
                <ChevronRight class="w-5 h-5 text-slate-400 group-hover:text-primary-600" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { uploadDocument, getDocuments, deleteDocument } from '../api'
import { getPortalProjectId, withPortalQuery } from '../utils/portal'
import { Upload, FileText, X, RotateCw, History, ChevronRight, Trash2 } from 'lucide-vue-next'

const router = useRouter()
const portalProjectId = getPortalProjectId()

const fileInput = ref(null)
const selectedFile = ref(null)
const documentName = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)
const loading = ref(false)
const documents = ref([])
const deleting = ref(false)
const deletingDocId = ref(null)

// 触发文件选择
const triggerFileInput = () => {
  fileInput.value.click()
}

// 处理文件选择
const handleFileChange = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
    documentName.value = file.name.replace(/\.[^/.]+$/, '') // 去掉扩展名
  }
}

// 处理文件拖放
const handleDrop = (e) => {
  const file = e.dataTransfer.files[0]
  if (file) {
    selectedFile.value = file
    documentName.value = file.name.replace(/\.[^/.]+$/, '')
  }
}

// 取消选择
const cancelSelection = () => {
  selectedFile.value = null
  documentName.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 上传文件
const uploadFile = async () => {
  if (!selectedFile.value || !documentName.value.trim()) return

  uploading.value = true
  uploadProgress.value = 0

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('name', documentName.value)

  try {
    // 模拟上传进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 200)

    const response = await uploadDocument(formData)

    clearInterval(progressInterval)
    uploadProgress.value = 100
    
    // 延迟跳转，让用户看到100%进度
    setTimeout(() => {
      router.push({
        name: 'parse',
        params: { documentId: response.doc_id },
        query: buildRouteQuery(documentName.value),
      })
    }, 500)

  } catch (error) {
    console.error('Upload failed:', error)
    alert('上传失败，请重试')
    uploadProgress.value = 0
  } finally {
    uploading.value = false
  }
}

// 获取文档列表
const fetchDocuments = async () => {
  loading.value = true
  try {
    const response = await getDocuments(portalProjectId)
    documents.value = response.documents || []
  } catch (error) {
    console.error('Failed to fetch documents:', error)
  } finally {
    loading.value = false
  }
}

const buildRouteQuery = (docName) => withPortalQuery({ docName })

// 选择已有文档
const selectDocument = (doc) => {
  router.push({
    name: 'parse',
    params: { documentId: doc.id },
    query: buildRouteQuery(doc.filename),
  })
}

// 删除文档
const handleDeleteDocument = async (doc, event) => {
  // 阻止事件冒泡，避免触发 selectDocument
  event.stopPropagation()
  
  // 确认删除
  if (!confirm(`确定要删除文档 "${doc.filename}" 吗？\n\n此操作将删除文档及其相关的所有数据（解析结果、验证结果等），且无法恢复。`)) {
    return
  }
  
  deleting.value = true
  deletingDocId.value = doc.id
  
  try {
    const response = await deleteDocument(doc.id)
    
    if (response.success) {
      // 显示删除成功信息
      alert('删除成功！')
      // 刷新文档列表
      await fetchDocuments()
    } else {
      alert('删除失败，请重试')
    }
  } catch (error) {
    console.error('Delete failed:', error)
    alert('删除失败：' + (error.response?.data?.error || error.message))
  } finally {
    deleting.value = false
    deletingDocId.value = null
  }
}

// 页面加载时获取文档列表
onMounted(() => {
  fetchDocuments()
})
</script>
