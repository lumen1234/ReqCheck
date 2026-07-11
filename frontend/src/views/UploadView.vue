<template>
 <div class="h-full overflow-y-auto p-8 bg-white">
 <div class="max-w-4xl mx-auto space-y-8">
 <div class="text-center space-y-2">
 <h1 class="text-3xl font-bold text-slate-900">欢迎使用文档审查系统</h1>
 <p class="text-slate-500 font-medium">上传您的文档以开始自动化审查分析</p>
 </div>

 <div class="bg-slate-50 border border-slate-200 rounded-xl p-8 shadow-sm space-y-6">
 <div class="grid grid-cols-2 gap-3 bg-white border border-slate-200 rounded-lg p-1">
 <button
 @click="switchUploadMode('file')"
 :class="uploadMode === 'file' ? 'bg-primary-900 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-50'"
 class="py-2.5 rounded-md font-bold transition-all"
 :disabled="uploading"
 >文件上传</button>
 <button
 @click="switchUploadMode('folder')"
 :class="uploadMode === 'folder' ? 'bg-primary-900 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-50'"
 class="py-2.5 rounded-md font-bold transition-all"
 :disabled="uploading"
 >文件夹上传</button>
 </div>

 <div v-if="uploadMode === 'file'">
 <div v-if="!selectedFile"
 class="border-2 border-dashed border-slate-300 rounded-lg p-12 text-center hover:border-primary-600 transition-colors cursor-pointer group bg-white"
 @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
 <input type="file" ref="fileInput" class="hidden" @change="handleFileChange" accept=".pdf,.doc,.docx,.txt,.md,.markdown" />
 <div class="flex flex-col items-center space-y-4">
 <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center group-hover:bg-primary-50 transition-colors">
 <Upload class="w-8 h-8 text-slate-400 group-hover:text-primary-600" />
 </div>
 <div class="space-y-1">
 <p class="text-lg font-bold text-slate-700">点击或拖拽文件至此处上传</p>
 <p class="text-sm text-slate-500">支持 .pdf, .doc, .docx, .txt, .md 等文档格式</p>
 </div>
 </div>
 </div>

 <div v-else class="space-y-6">
 <div class="flex items-center justify-between p-4 bg-white border border-slate-200 rounded-lg">
 <div class="flex items-center space-x-4">
 <div class="w-12 h-12 bg-primary-50 rounded flex items-center justify-center">
 <FileText class="w-7 h-7 text-primary-600" />
 </div>
 <div>
 <p class="text-sm font-bold text-slate-700">{{ selectedFile.name }}</p>
 <p class="text-xs text-slate-500">{{ formatSize(selectedFile.size) }}</p>
 </div>
 </div>
 <button @click="cancelSelection" class="text-slate-400 hover:text-red-500 transition-colors" v-if="!uploading">
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
 </div>

 <div v-else>
 <div v-if="selectedFolderFiles.length ===0"
 class="border-2 border-dashed border-slate-300 rounded-lg p-12 text-center hover:border-primary-600 transition-colors cursor-pointer group bg-white"
 @click="triggerFolderInput" @dragover.prevent @drop.prevent="handleFolderDrop">
 <input type="file" ref="folderInput" class="hidden" multiple webkitdirectory directory @change="handleFolderChange" accept=".pdf,.doc,.docx,.txt,.md,.markdown" />
 <div class="flex flex-col items-center space-y-4">
 <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center group-hover:bg-primary-50 transition-colors">
 <FolderUp class="w-8 h-8 text-slate-400 group-hover:text-primary-600" />
 </div>
 <div class="space-y-1">
 <p class="text-lg font-bold text-slate-700">点击选择包含多个需求规格文档的文件夹</p>
 <p class="text-sm text-slate-500">进入文档分析页后会自动批量解析，并显示进度条</p>
 </div>
 </div>
 </div>

 <div v-else class="space-y-6">
 <div class="p-4 bg-white border border-slate-200 rounded-lg space-y-4">
 <div class="flex items-center justify-between">
 <div class="flex items-center space-x-4">
 <div class="w-12 h-12 bg-primary-50 rounded flex items-center justify-center">
 <FolderUp class="w-7 h-7 text-primary-600" />
 </div>
 <div>
 <p class="text-sm font-bold text-slate-700">{{ folderName }}</p>
 <p class="text-xs text-slate-500">{{ selectedFolderFiles.length }} 个文档，{{ formatSize(folderTotalSize) }}</p>
 </div>
 </div>
 <button @click="cancelSelection" class="text-slate-400 hover:text-red-500 transition-colors" v-if="!uploading">
 <X class="w-5 h-5" />
 </button>
 </div>
 <div class="max-h-48 overflow-y-auto divide-y divide-slate-100 border border-slate-100 rounded">
 <div v-for="(file, index) in selectedFolderFiles" :key="file.webkitRelativePath || file.name" class="px-3 py-2 text-sm flex justify-between gap-4">
 <span class="font-medium text-slate-700">{{ index +1 }}. {{ file.webkitRelativePath || file.name }}</span>
 <span class="text-slate-400 shrink-0">{{ formatSize(file.size) }}</span>
 </div>
 </div>
 </div>

 <button @click="uploadFolderFiles" :disabled="uploading || selectedFolderFiles.length ===0"
 class="w-full py-3 bg-primary-900 hover:bg-primary-800 disabled:bg-slate-300 text-white font-bold rounded-lg transition-all shadow-md flex items-center justify-center space-x-2">
 <Upload class="w-5 h-5" v-if="!uploading" />
 <RotateCw class="w-5 h-5 animate-spin" v-else />
 <span>{{ uploading ? '正在上传文件夹...' : '确认上传文件夹并开始分析' }}</span>
 </button>
 </div>
 </div>

 <div v-if="uploading" class="mt-6 space-y-2">
 <div class="flex justify-between text-sm mb-1 font-medium text-slate-600">
 <span>{{ uploadMode === 'folder' ? '正在上传文件夹...' : '正在上传文档...' }}</span>
 <span>{{ uploadProgress }}%</span>
 </div>
 <div class="w-full bg-slate-200 rounded-full h-2">
 <div class="bg-primary-600 h-2 rounded-full transition-all duration-300" :style="{ width: uploadProgress + '%' }"></div>
 </div>
 </div>
 </div>

 <div class="space-y-4">
 <div class="flex items-center justify-between border-b border-slate-100 pb-2">
 <h2 class="text-xl font-bold flex items-center gap-2 text-slate-800">
 <History class="w-5 h-5 text-primary-600" />
 {{ uniPortalMode ? '项目列表（UniPortal + 本地上传）' : '历史文档（本地上传）' }}
 </h2>
 <button @click="fetchDocuments" class="text-sm font-semibold text-primary-600 hover:text-primary-700">刷新列表</button>
 </div>

 <div v-if="loading" class="text-center py-12">
 <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
 </div>

 <div v-else-if="documents.length ===0" class="bg-slate-50 border border-slate-200 rounded-lg p-12 text-center">
 <p class="text-slate-400 font-medium">暂无文档，请先上传一个</p>
 </div>

 <div v-else class="grid grid-cols-1 gap-4">
 <div v-for="doc in documents" :key="doc.id" class="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-all cursor-pointer group" @click="selectDocument(doc)">
 <div class="flex items-center justify-between">
 <div class="flex items-center space-x-4">
 <div class="w-10 h-10 bg-primary-50 rounded flex items-center justify-center">
 <FolderUp v-if="isBatchDoc(doc)" class="w-6 h-6 text-primary-600" />
 <FileText v-else class="w-6 h-6 text-primary-600" />
 </div>
 <div>
 <div class="flex items-center gap-2">
 <p class="text-sm font-bold text-slate-900">{{ doc.filename }}</p>
 <span v-if="isBatchDoc(doc)" class="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-purple-100 text-purple-800">文件夹 · {{ doc.file_count ||0 }} 个</span>
 <span v-else-if="doc.source === 'uniportal'" class="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-blue-100 text-blue-800">UniPortal</span>
 <span v-else-if="doc.source === 'local'" class="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-slate-100 text-slate-600">本地</span>
 </div>
 <p class="text-xs text-slate-500">{{ doc.upload_time }}</p>
 </div>
 </div>
 <div class="flex items-center space-x-2">
 <button v-if="doc.source !== 'uniportal'" @click="handleDeleteDocument(doc, $event)" :disabled="deleting && deletingDocId === doc.id" class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-all disabled:opacity-50" :title="isBatchDoc(doc) ? '删除文件夹' : '删除文档'">
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
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { uploadDocument, uploadFolder, getDocuments, deleteDocument } from '../api'
import { getPortalProjectId, withPortalQuery, isUniPortalMode } from '../utils/portal'
import { Upload, FileText, X, RotateCw, History, ChevronRight, Trash2, FolderUp } from 'lucide-vue-next'

const router = useRouter()
const portalProjectId = computed(() => getPortalProjectId())
const uniPortalMode = computed(() => isUniPortalMode())

const uploadMode = ref('file')
const fileInput = ref(null)
const folderInput = ref(null)
const selectedFile = ref(null)
const selectedFolderFiles = ref([])
const documentName = ref('')
const folderName = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)
const loading = ref(false)
const documents = ref([])
const deleting = ref(false)
const deletingDocId = ref(null)

const folderTotalSize = computed(() => selectedFolderFiles.value.reduce((sum, file) => sum + file.size,0))
const supportedExt = /\.(pdf|doc|docx|txt|md|markdown)$/i

const formatSize = (size) => `${(size /1024).toFixed(2)} KB`
const isBatchDoc = (doc) => doc.kind === 'batch' || doc.source === 'local_batch' || doc.file_type === 'folder'
const buildRouteQuery = (docName, extra = {}) => withPortalQuery({ docName, ...extra })

const switchUploadMode = (mode) => {
 if (uploading.value) return
 uploadMode.value = mode
 cancelSelection()
}

const triggerFileInput = () => fileInput.value.click()
const triggerFolderInput = () => folderInput.value.click()

const handleFileChange = (e) => {
 const file = e.target.files[0]
 if (file) {
 selectedFile.value = file
 documentName.value = file.name.replace(/\.[^/.]+$/, '')
 }
}

const handleFolderChange = (e) => setFolderFiles(Array.from(e.target.files || []))
const handleDrop = (e) => {
 const file = e.dataTransfer.files[0]
 if (file) {
 selectedFile.value = file
 documentName.value = file.name.replace(/\.[^/.]+$/, '')
 }
}
const handleFolderDrop = (e) => setFolderFiles(Array.from(e.dataTransfer.files || []))

const setFolderFiles = (files) => {
 const validFiles = files.filter((file) => supportedExt.test(file.name))
 selectedFolderFiles.value = validFiles.sort((a, b) => (a.webkitRelativePath || a.name).localeCompare(b.webkitRelativePath || b.name))
 const first = selectedFolderFiles.value[0]
 folderName.value = first?.webkitRelativePath?.split('/')[0] || '文件夹上传'
}

const cancelSelection = () => {
 selectedFile.value = null
 selectedFolderFiles.value = []
 documentName.value = ''
 folderName.value = ''
 if (fileInput.value) fileInput.value.value = ''
 if (folderInput.value) folderInput.value.value = ''
}

const runUploadProgress = () => setInterval(() => {
 if (uploadProgress.value <90) uploadProgress.value +=10
},200)

const uploadFile = async () => {
 if (!selectedFile.value || !documentName.value.trim()) return
 uploading.value = true
 uploadProgress.value =0
 const formData = new FormData()
 formData.append('file', selectedFile.value)
 formData.append('name', documentName.value)
 const progressInterval = runUploadProgress()
 try {
 const response = await uploadDocument(formData)
 clearInterval(progressInterval)
 uploadProgress.value =100
 setTimeout(() => {
 router.push({ name: 'parse', params: { documentId: response.doc_id }, query: buildRouteQuery(documentName.value) })
 },500)
 } catch (error) {
 clearInterval(progressInterval)
 console.error('Upload failed:', error)
 alert('上传失败，请重试')
 uploadProgress.value =0
 } finally {
 uploading.value = false
 }
}

const uploadFolderFiles = async () => {
 if (selectedFolderFiles.value.length ===0) return
 uploading.value = true
 uploadProgress.value =0
 const formData = new FormData()
 formData.append('folder_name', folderName.value || '文件夹上传')
 selectedFolderFiles.value.forEach((file) => {
 formData.append('files', file)
 formData.append('relative_paths', file.webkitRelativePath || file.name)
 })
 const progressInterval = runUploadProgress()
 try {
 const response = await uploadFolder(formData)
 clearInterval(progressInterval)
 uploadProgress.value =100
 setTimeout(() => {
 router.push({ name: 'parse', params: { documentId: response.batch_id }, query: buildRouteQuery(response.batch_name || folderName.value, { mode: 'batch' }) })
 },500)
 } catch (error) {
 clearInterval(progressInterval)
 console.error('Folder upload failed:', error)
 alert(error.response?.data?.error || '文件夹上传失败，请重试')
 uploadProgress.value =0
 } finally {
 uploading.value = false
 }
}

const fetchDocuments = async () => {
 loading.value = true
 try {
 const response = await getDocuments(portalProjectId.value)
 documents.value = response.documents || []
 } catch (error) {
 console.error('Failed to fetch documents:', error)
 } finally {
 loading.value = false
 }
}

const selectDocument = (doc) => {
 router.push({
 name: 'parse',
 params: { documentId: doc.id },
 query: buildRouteQuery(doc.filename, isBatchDoc(doc) ? { mode: 'batch' } : {}),
 })
}

const handleDeleteDocument = async (doc, event) => {
 event.stopPropagation()
 const isFolder = isBatchDoc(doc)
 const label = isFolder ? '文件夹' : '文档'
 if (!confirm(`确定要删除${label} "${doc.filename}" 吗？\n\n此操作将删除${label}及其相关的所有数据（解析结果、验证结果等），且无法恢复。`)) return
 deleting.value = true
 deletingDocId.value = doc.id
 try {
 const response = await deleteDocument(doc.id)
 if (response.success) {
 alert('删除成功！')
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

onMounted(() => fetchDocuments())
</script>
