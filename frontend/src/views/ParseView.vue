<template>
 <div class="h-full flex flex-col bg-white">
 <div class="border-b border-slate-200 px-8 py-6">
 <div class="max-w-7xl mx-auto flex items-center justify-between gap-4">
 <div>
 <h1 class="text-3xl font-bold text-slate-900">文档分析</h1>
 <p class="text-slate-500 font-medium mt-2">{{ isBatchMode ? '批量解析文件夹内文档，并通过文档转换器查看结果' : '解析文档并提取需求结构树' }}</p>
 </div>
 <button @click="refreshParse" :disabled="loading" class="px-4 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-all flex items-center gap-2" title="重新解析文档">
 <RotateCw class="w-4 h-4" :class="{ 'animate-spin': loading }" />
 刷新
 </button>
 </div>
 <div v-if="isBatchMode" class="max-w-7xl mx-auto mt-3 space-y-2">
 <div v-if="showParseProgress" class="bg-slate-50 border border-slate-200 rounded-md px-3 py-2 space-y-1.5">
 <div class="flex items-center justify-between text-xs font-medium text-slate-600">
 <span>正在解析：{{ parseProgress.current || '准备中' }}</span>
 <span>{{ parseProgress.done }} / {{ parseProgress.total }}</span>
 </div>
 <div class="w-full bg-slate-200 rounded-full h-1.5">
 <div class="bg-primary-600 h-1.5 rounded-full transition-all duration-300" :style="{ width: progressPercent + '%' }"></div>
 </div>
 </div>
 <div v-if="!showParseProgress && parseProgress.errors.length" class="text-[11px] text-red-600 leading-snug">
 解析失败：{{ parseProgress.errors.map(e => e.filename).join('、') }}
 </div>
 <div class="flex flex-wrap items-center gap-1.5">
 <span class="text-xs font-semibold text-slate-600 mr-0.5">文档转换器</span>
 <button @click="setDocFilter('all')" :class="selectedDocFilter === 'all' ? 'bg-primary-900 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'" class="px-2 py-0.5 rounded text-xs font-medium transition-all">全部</button>
 <button v-for="doc in batchDocuments" :key="doc.doc_id" @click="setDocFilter(doc.doc_id)" :class="selectedDocFilter === doc.doc_id ? 'bg-primary-900 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'" class="px-2 py-0.5 rounded text-xs font-medium transition-all max-w-[14rem] truncate" :title="doc.filename">
 doc {{ doc.doc }}：{{ doc.filename }}
 </button>
 </div>
 </div>
 </div>

 <div class="flex-1 overflow-hidden flex">
 <div class="w-1/3 border-r border-slate-200 overflow-y-auto flex flex-col">
 <div class="px-6 pt-4 pb-2 border-b border-slate-100">
 <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">内容分块关键词</label>
 <div class="flex gap-2">
 <input v-model="splitKeyword" type="text" placeholder="输入分块关键词..." class="flex-1 px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500" @keyup.enter="applySplit" />
 <button @click="applySplit" class="px-3 py-1.5 text-sm font-semibold bg-primary-900 hover:bg-primary-800 text-white rounded-lg transition-all">应用</button>
 </div>
 </div>
 <div class="flex-1 overflow-y-auto p-6">
 <RequirementTree :loading="loading" :tree-data="treeData" @node-click="handleNodeClick" @load-mock-data="loadMockData" />
 </div>
 </div>
 <div class="flex-1 overflow-y-auto p-8">
 <div v-if="selectedNode" :key="selectedNode.id" class="max-w-3xl space-y-6">
 <div class="space-y-2">
 <div class="flex items-center space-x-2">
 <span class="px-2 py-1 bg-primary-100 text-primary-900 text-xs font-semibold rounded">Level {{ selectedNode.level }}</span>
 <span v-if="selectedNode.doc" class="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-semibold rounded">doc {{ selectedNode.doc }}</span>
 </div>
 <h2 class="text-2xl font-bold text-slate-900">{{ selectedNode.label }}</h2>
 <p class="text-xs text-slate-500 font-mono">ID: {{ selectedNode.id }}</p>
 <p v-if="selectedNode.source_filename" class="text-xs text-slate-500">来源文档：{{ selectedNode.source_filename }}</p>
 </div>
 <div v-if="hasNodeContent(selectedNode)" class="space-y-3">
 <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide">需求内容</h3>
 <div class="bg-slate-50 border border-slate-200 rounded-lg p-6 space-y-4">
 <div v-if="selectedNode.images && selectedNode.images.length" class="space-y-4">
 <figure v-for="img in selectedNode.images" :key="img.id" class="text-center">
 <img :key="`${selectedNode.id}-${img.id}`" :src="`${img.path}?doc=${selectedNode.doc_id || documentId}`" :alt="img.caption || img.alt || '图片'" class="max-w-full mx-auto border border-slate-200 rounded-lg bg-white min-h-[80px]" loading="eager" decoding="async" @error="onImageError($event, img)" />
 <figcaption v-if="img.caption || img.alt" class="text-xs text-slate-500 mt-2">{{ img.caption || img.alt }}</figcaption>
 </figure>
 </div>
 <div v-if="selectedNode.content_html" ref="contentHtmlRef" class="parse-content prose prose-sm max-w-none text-slate-700" v-html="selectedNode.content_html" />
 <div v-if="selectedNode.tables && selectedNode.tables.length" class="space-y-4"><div v-for="tbl in selectedNode.tables" :key="tbl.id || tbl.caption" class="overflow-x-auto" v-html="tableToHtml(tbl)" /></div>
 <p v-if="!selectedNode.content_html && selectedNode.content && !(selectedNode.content_blocks && selectedNode.content_blocks.length)" class="text-slate-700 leading-relaxed whitespace-pre-wrap">{{ selectedNode.content }}</p>
 </div>
 </div>
 <div v-if="selectedNode.children && selectedNode.children.length >0" class="space-y-3">
 <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide">子需求</h3>
 <div class="grid grid-cols-2 gap-3"><div v-for="child in selectedNode.children" :key="child.id" @click="selectNode(child)" class="p-4 bg-white border border-slate-200 rounded-lg hover:border-primary-400 hover:shadow-md transition-all cursor-pointer"><p class="text-sm font-semibold text-slate-900 mb-1">{{ child.label }}</p><p class="text-xs text-slate-500">{{ child.id }}</p></div></div>
 </div>
 </div>
 <div v-else class="flex items-center justify-center h-full text-slate-400"><div class="text-center"><FileText class="w-16 h-16 mx-auto mb-4 opacity-50" /><p class="text-sm">请从左侧选择需求节点</p></div></div>
 </div>
 </div>
 <div class="border-t border-slate-200 px-8 py-4 bg-slate-50">
 <div class="max-w-7xl mx-auto flex justify-end">
 <button @click="goToNext" class="px-6 py-2.5 bg-primary-900 hover:bg-primary-800 text-white font-bold rounded-lg transition-all shadow-sm flex items-center space-x-2">
 <span>进入需求验证</span>
 <ChevronRight class="w-4 h-4" />
 </button>
 </div>
 </div>
 </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getParseResult, getBatchDetail } from '../api'
import { FileText, ChevronRight, RotateCw } from 'lucide-vue-next'
import RequirementTree from '../components/RequirementTree.vue'
import { withPortalQuery } from '../utils/portal'
import { renderMathInElement } from '../utils/mathRender'

const router = useRouter()
const route = useRoute()
const documentId = computed(() => route.params.documentId)
const documentName = computed(() => route.query.docName || '未命名文档')
const isBatchMode = computed(() => route.query.mode === 'batch')
const loading = ref(false)
const requirementTree = ref(null)
const selectedNode = ref(null)
const savedKw = localStorage.getItem('reqcheck_split_keyword') || '需求标识'
const splitKeyword = ref(savedKw)
const activeSplitBy = ref(savedKw)
const applySplit = () => {
  activeSplitBy.value = splitKeyword.value.trim()
  localStorage.setItem("reqcheck_split_keyword", activeSplitBy.value)
  isBatchMode.value ? loadBatch(true) : loadRequirementTree(true)
}
const contentHtmlRef = ref(null)
const batchDocuments = ref([])
const docTreesById = ref({})
const selectedDocFilter = ref('all')
const parseProgress = ref({ total:0, done:0, current: '', errors: [] })
const progressPercent = computed(() => parseProgress.value.total ? Math.round(parseProgress.value.done / parseProgress.value.total *100) :0)
const showParseProgress = computed(() => {
 const { total, done } = parseProgress.value
 return loading.value || (total > 0 && done < total)
})

const renderNodeMath = () => nextTick(() => renderMathInElement(contentHtmlRef.value))
const hasNodeContent = (node) => Boolean(node && (node.content || node.content_html || node.images?.length || node.tables?.length))
const transformNode = (node, meta = {}) => {
 const transformed = { id: node.id, label: node.display_title || node.label || '未命名节点', content: node.content ?? '', content_html: node.content_html ?? '', display_title: node.display_title, number: node.number, level: node.level ||1, v_status: node.v_status ?? '', e_status: node.e_status ?? '', tables: node.tables, images: node.images, content_blocks: node.content_blocks || [], doc: meta.doc ?? node.doc, doc_id: meta.doc_id ?? node.doc_id, source_filename: meta.filename ?? node.source_filename, children: [] }
 transformed.children = (node.children || []).map((child) => transformNode(child, meta))
 return transformed
}
const convertToTreeData = (jsonData, meta = {}) => Array.isArray(jsonData) ? jsonData.map((node) => transformNode(node, meta)) : []
const combinedTreeData = computed(() => batchDocuments.value.map((doc) => ({ id: `doc-${doc.doc}`, label: `文档 ${doc.doc}：${doc.filename}`, level:1, doc: doc.doc, doc_id: doc.doc_id, source_filename: doc.filename, children: convertToTreeData(docTreesById.value[doc.doc_id]?.children || [], doc) })))
const treeData = computed(() => {
 if (!isBatchMode.value) return convertToTreeData(requirementTree.value)
 if (selectedDocFilter.value === 'all') return combinedTreeData.value
 const doc = batchDocuments.value.find((item) => item.doc_id === selectedDocFilter.value) || {}
 return convertToTreeData(docTreesById.value[selectedDocFilter.value]?.children || [], doc)
})
const pickFirstWithContent = (nodes) => {
 for (const node of nodes || []) {
 if (hasNodeContent(node)) return node
 const found = pickFirstWithContent(node.children)
 if (found) return found
 }
 return nodes?.[0] ?? null
}
const selectNode = (node) => { selectedNode.value = node ? { ...node } : null; renderNodeMath() }
const selectContentBlock = (block) => {
  selectedNode.value = {
    id: block.id,
    label: block.label,
    content: block.content,
    tables: block.tables || [],
    level: (selectedNode.value?.level || 0) + 1,
    _isVirtual: true,
    children: [],
  }
}
const handleNodeClick = (data) => selectNode(data)
const selectInitialNode = () => selectNode(pickFirstWithContent(treeData.value))
const setDocFilter = (filter) => { selectedDocFilter.value = filter; nextTick(selectInitialNode) }
const escapeHtml = (text) => String(text ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const tableToHtml = (table) => {
 const headers = table?.headers || []
 const rows = table?.rows || []
 if (!headers.length && !rows.length) return ''
 let html = '<table class="req-table" border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">'
 if (headers.length) html += `<thead><tr>${headers.map((h) => `<th style="border:1px solid #ccc;padding:6px;background:#f5f5f5">${escapeHtml(h)}</th>`).join('')}</tr></thead>`
 if (rows.length) html += `<tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td style="border:1px solid #ccc;padding:6px">${escapeHtml(cell)}</td>`).join('')}</tr>`).join('')}</tbody>`
 return html + '</table>'
}
const onImageError = (event, img) => { console.warn('图片加载失败，请重新解析文档:', img?.path); event.target?.classList.add('opacity-50') }
const loadRequirementTree = async (force = false) => {
 if (!documentId.value) return
 loading.value = true
 try {
 const result = await getParseResult(documentId.value, { force, splitBy: activeSplitBy.value })
 requirementTree.value = result.requirement_tree.children || null
 selectInitialNode()
 } catch (error) {
 console.error('Failed to load requirement tree:', error)
 const msg = error.response?.data?.error || error.message || '解析失败'
 alert(msg)
 } finally { loading.value = false }
}
const loadBatchRequirementTrees = async (force = false) => {
 loading.value = true
 docTreesById.value = {}
 parseProgress.value = { total: batchDocuments.value.length, done:0, current: '', errors: [] }
 for (const doc of batchDocuments.value) {
 parseProgress.value.current = doc.filename
 try {
 const result = await getParseResult(doc.doc_id, { force, splitBy: activeSplitBy.value })
 docTreesById.value[doc.doc_id] = result.requirement_tree
 } catch (error) {
 const msg = error.response?.data?.error || error.message || '解析失败'
 parseProgress.value.errors.push({ doc_id: doc.doc_id, filename: doc.filename, error: msg })
 } finally { parseProgress.value.done +=1 }
 }
 if (parseProgress.value.errors.length) {
 alert('部分文档解析失败：\n' + parseProgress.value.errors.map((e) => `${e.filename}: ${e.error}`).join('\n'))
 }
 selectedDocFilter.value = 'all'
 selectInitialNode()
 loading.value = false
}
const loadBatch = async (force = false) => {
 if (!documentId.value) return
 loading.value = true
 try {
 const result = await getBatchDetail(documentId.value)
 batchDocuments.value = result.documents || []
 } catch (error) { console.error('Failed to load batch:', error); loading.value = false; return }
 await loadBatchRequirementTrees(force)
}
const refreshParse = () => isBatchMode.value ? loadBatch(true) : loadRequirementTree(true)
const goToNext = () => {
 if (isBatchMode.value) router.push({ name: 'validate', params: { documentId: documentId.value }, query: withPortalQuery({ docName: documentName.value, mode: 'batch', splitBy: activeSplitBy.value }) })
 else router.push({ name: 'validate', params: { documentId: documentId.value }, query: withPortalQuery({ docName: documentName.value, splitBy: activeSplitBy.value }) })
}
const loadMockData = () => { requirementTree.value = [{ id: 'req-1', label: '示例需求', content: '示例内容', level:1, children: [] }]; selectInitialNode() }
onMounted(() => { isBatchMode.value ? loadBatch() : loadRequirementTree() })
watch(() => selectedNode.value?.content_html, () => renderNodeMath())
</script>

<style scoped>
.parse-content :deep(.req-table) { width:100%; border-collapse: collapse; margin:12px0; display: table; }
.parse-content :deep(.req-table th), .parse-content :deep(.req-table td) { border:1px solid #ccc; padding:6px; vertical-align: top; }
.parse-content :deep(.req-table th) { background: #f5f5f5; }
.parse-content :deep(.math-block) { margin:12px0; overflow-x: auto; text-align: center; }
.parse-content :deep(.math-inline) { display: inline-block; vertical-align: middle; }
</style>
