<template>
  <div class="h-full flex flex-col bg-white">
    <!-- Header -->
    <div class="border-b border-slate-200 px-8 py-6">
      <div class="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold text-slate-900">需求验证</h1>
          <p class="text-slate-500 font-medium mt-2">
            {{ isBatchMode ? '批量验证文件夹内文档，并通过文档转换器查看结果' : '审查软件需求文档完整性与准确性' }}
          </p>
        </div>

        <div class="flex items-center space-x-4">
          <button
            @click="refreshValidate(true)"
            :disabled="loading"
            class="px-4 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-all flex items-center gap-2"
            title="重新验证文档"
          >
            <RotateCw class="w-4 h-4" :class="{ 'animate-spin': loading }" />
            刷新
          </button>

          <template v-if="displayValidationData.length > 0">
            <div class="text-center px-4 py-2 bg-slate-50 rounded-lg">
              <p class="text-xs text-slate-500 font-medium">总需求数</p>
              <p class="text-2xl font-bold text-slate-900">{{ totalCount }}</p>
            </div>
            <div class="text-center px-4 py-2 bg-green-50 rounded-lg">
              <p class="text-xs text-green-600 font-medium">验证通过</p>
              <p class="text-2xl font-bold text-green-700">{{ passedCount }}</p>
            </div>
            <div class="text-center px-4 py-2 bg-red-50 rounded-lg">
              <p class="text-xs text-red-600 font-medium">验证失败</p>
              <p class="text-2xl font-bold text-red-700">{{ failedCount }}</p>
            </div>
            <div class="text-center px-4 py-2 bg-blue-50 rounded-lg">
              <p class="text-xs text-blue-600 font-medium">通过率</p>
              <p class="text-2xl font-bold text-blue-700">{{ passRate }}%</p>
            </div>
          </template>
        </div>
      </div>

      <div v-if="isBatchMode" class="max-w-7xl mx-auto mt-3 space-y-2">
        <div v-if="showValidateProgress" class="bg-slate-50 border border-slate-200 rounded-md px-3 py-2 space-y-1.5">
          <div class="flex items-center justify-between text-xs font-medium text-slate-600">
            <span>正在验证：{{ validateProgress.current || '准备中' }}</span>
            <span>{{ validateProgress.done }} / {{ validateProgress.total }}</span>
          </div>
          <div class="w-full bg-slate-200 rounded-full h-1.5">
            <div class="bg-primary-600 h-1.5 rounded-full transition-all duration-300" :style="{ width: progressPercent + '%' }"></div>
          </div>
        </div>
        <div v-if="!showValidateProgress && validateProgress.errors.length" class="text-[11px] text-red-600 leading-snug">
          验证失败：{{ validateProgress.errors.map(e => e.filename).join('、') }}
        </div>
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="text-xs font-semibold text-slate-600 mr-0.5">文档转换器</span>
          <button
            @click="setDocFilter('all')"
            :class="selectedDocFilter === 'all' ? 'bg-primary-900 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'"
            class="px-2 py-0.5 rounded text-xs font-medium transition-all"
          >全部</button>
          <button
            v-for="doc in batchDocuments"
            :key="doc.doc_id"
            @click="setDocFilter(doc.doc_id)"
            :class="selectedDocFilter === doc.doc_id ? 'bg-primary-900 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'"
            class="px-2 py-0.5 rounded text-xs font-medium transition-all max-w-[14rem] truncate"
            :title="doc.filename"
          >
            doc {{ doc.doc }}：{{ doc.filename }}
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content - List View -->
    <div class="flex-1 overflow-y-auto p-8">
      <div class="max-w-7xl mx-auto">
        <div v-if="loading && displayValidationData.length === 0" class="text-center py-12">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p class="text-slate-600 mt-4">{{ isBatchMode ? '正在逐文档验证...' : '加载验证结果...' }}</p>
        </div>

        <div v-else-if="displayValidationData.length === 0" class="text-center py-12">
          <FileText class="w-16 h-16 mx-auto mb-4 text-slate-300" />
          <p class="text-slate-500 mb-4">暂无验证数据</p>
          <button
            @click="refreshValidate(false)"
            class="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white text-sm font-semibold rounded-lg transition-all"
          >
            重新加载
          </button>
          <button
            @click="refreshValidate(true)"
            class="ml-2 px-4 py-2 bg-slate-600 hover:bg-slate-700 text-white text-sm font-semibold rounded-lg transition-all"
          >
            强制重新验证
          </button>
        </div>

        <div v-else>
          <div
            v-if="showFallbackWarning"
            class="mb-4 p-4 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm leading-relaxed"
          >
            当前结果是<strong>历史缓存</strong>，生成时大模型 API 调用失败（配置未生效或 Base URL 有误）。
            LLM 配置已更新后，请点击右上角 <strong>刷新</strong> 重新审查。
            <span v-if="isCached" class="block mt-1 text-amber-700">（本次加载使用了缓存，未重新调用大模型）</span>
          </div>

          <div class="space-y-3">
            <div
              v-for="item in displayValidationData"
              :key="`${item.doc_id || 'single'}-${item.id}`"
              class="validation-item bg-white border rounded-lg transition-all hover:shadow-md"
              :class="[
                item.result ? 'border-green-200 hover:border-green-300' : 'border-red-200 hover:border-red-300',
                { 'ml-0': item.level === 0, 'ml-8': item.level === 1, 'ml-16': item.level === 2, 'ml-24': item.level === 3 }
              ]"
            >
              <div class="p-4">
                <div class="flex items-start justify-between">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-3 mb-2">
                      <div
                        class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                        :class="item.result ? 'bg-green-100' : 'bg-red-100'"
                      >
                        <CheckCircle v-if="item.result" class="w-4 h-4 text-green-600" />
                        <XCircle v-else class="w-4 h-4 text-red-600" />
                      </div>
                      <h3 class="text-base font-bold text-slate-900 truncate">{{ item.name }}</h3>
                      <span v-if="item.doc" class="flex-shrink-0 px-2 py-0.5 bg-purple-100 text-purple-800 text-xs font-medium rounded">
                        doc {{ item.doc }}
                      </span>
                      <span class="flex-shrink-0 px-2 py-0.5 bg-slate-100 text-slate-600 text-xs font-medium rounded">
                        L{{ item.level }}
                      </span>
                    </div>
                    <div class="ml-9">
                      <p class="text-sm text-slate-600 leading-relaxed">{{ item.reason }}</p>
                      <p v-if="item.source_filename" class="text-xs text-slate-400 mt-1">来源：{{ item.source_filename }}</p>
                      <p class="text-xs text-slate-400 font-mono mt-1">ID: {{ item.id }}</p>
                    </div>
                  </div>
                  <div class="flex-shrink-0 ml-4">
                    <span
                      class="px-3 py-1 text-xs font-bold rounded-full"
                      :class="item.result ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                    >
                      {{ item.result ? '✓ 通过' : '✗ 未通过' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Action Bar -->
    <div class="border-t border-slate-200 px-8 py-4 bg-slate-50">
      <div class="max-w-7xl mx-auto flex justify-end">
        <button
          @click="goToNext"
          :disabled="!canGoNext"
          class="px-6 py-2.5 bg-primary-900 hover:bg-primary-800 disabled:bg-slate-300 text-white font-bold rounded-lg transition-all shadow-sm flex items-center space-x-2"
        >
          <span>进入文档导出</span>
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getReviewResult, getBatchDetail } from '../api'
import { withPortalQuery } from '../utils/portal'
import { FileText, ChevronRight, CheckCircle, XCircle, RotateCw } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

const documentId = computed(() => route.params.documentId)
const documentName = computed(() => route.query.docName || '未命名文档')
const isBatchMode = computed(() => route.query.mode === 'batch')

const loading = ref(false)
const validationData = ref([])
const isCached = ref(false)
const batchDocuments = ref([])
const resultsByDocId = ref({})
const selectedDocFilter = ref('all')
const validateProgress = ref({ total: 0, done: 0, current: '', errors: [] })

const FALLBACK_REASON_MARKERS = [
  '由于网络原因，大模型验证暂时不可用',
  '由于大模型验证暂时不可用',
  '大模型 API 调用失败',
]

const progressPercent = computed(() =>
  validateProgress.value.total
    ? Math.round((validateProgress.value.done / validateProgress.value.total) * 100)
    : 0
)
const showValidateProgress = computed(() => {
  const { total, done } = validateProgress.value
  return loading.value || (total > 0 && done < total)
})

const displayValidationData = computed(() => {
  if (!isBatchMode.value) return validationData.value
  if (selectedDocFilter.value === 'all') {
    return batchDocuments.value.flatMap((doc) => resultsByDocId.value[doc.doc_id] || [])
  }
  return resultsByDocId.value[selectedDocFilter.value] || []
})

const showFallbackWarning = computed(() =>
  displayValidationData.value.some((item) =>
    FALLBACK_REASON_MARKERS.some((marker) => (item.reason || '').includes(marker))
  )
)

const totalCount = computed(() => displayValidationData.value.length)
const passedCount = computed(() => displayValidationData.value.filter((item) => item.result === true).length)
const failedCount = computed(() => displayValidationData.value.filter((item) => item.result === false).length)
const passRate = computed(() => (totalCount.value === 0 ? 0 : Math.round((passedCount.value / totalCount.value) * 100)))
const canGoNext = computed(() => displayValidationData.value.length > 0 || Object.keys(resultsByDocId.value).length > 0)

const calculateLevel = (nodeId, parentId, allNodes) => {
  if (!parentId || parentId === '' || parentId === null || nodeId === 'root') return 0
  const parent = allNodes.find((n) => n.id === parentId)
  if (!parent) return 1
  return 1 + calculateLevel(parent.id, parent.parent_id, allNodes)
}

const processValidationData = (data, meta = {}) => {
  if (!data || !Array.isArray(data)) return []
  return data.map((node) => ({
    ...node,
    level: calculateLevel(node.id, node.parent_id, data),
    doc: meta.doc,
    doc_id: meta.doc_id,
    source_filename: meta.filename,
  }))
}

const setDocFilter = (filter) => {
  selectedDocFilter.value = filter
}

const fetchOneDocValidation = async (docId, force = false, meta = {}) => {
  const result = await getReviewResult(docId, force ? { force: 1 } : {})
  const rawData = result.validation_results || result
  if (!Array.isArray(rawData)) throw new Error('验证结果格式异常')
  return {
    cached: Boolean(result.cached),
    items: processValidationData(rawData, meta),
  }
}

const loadValidateResult = async (force = false) => {
  if (!documentId.value) return
  loading.value = true
  isCached.value = false
  try {
    const { cached, items } = await fetchOneDocValidation(documentId.value, force)
    isCached.value = cached
    validationData.value = items
  } catch (error) {
    console.error('Failed to load validate result:', error)
    const msg = error.response?.data?.error || error.message || '验证失败'
    alert(msg)
    validationData.value = []
  } finally {
    loading.value = false
  }
}

const loadBatchValidations = async (force = false) => {
  if (!documentId.value) return
  loading.value = true
  resultsByDocId.value = {}
  validateProgress.value = { total: batchDocuments.value.length, done: 0, current: '', errors: [] }
  let anyCached = false
  for (const doc of batchDocuments.value) {
    validateProgress.value.current = doc.filename
    try {
      const { cached, items } = await fetchOneDocValidation(doc.doc_id, force, {
        doc: doc.doc,
        doc_id: doc.doc_id,
        filename: doc.filename,
      })
      resultsByDocId.value[doc.doc_id] = items
      if (cached) anyCached = true
    } catch (error) {
      const msg = error.response?.data?.error || error.message || '验证失败'
      validateProgress.value.errors.push({ doc_id: doc.doc_id, filename: doc.filename, error: msg })
      resultsByDocId.value[doc.doc_id] = []
    } finally {
      validateProgress.value.done += 1
    }
  }
  isCached.value = anyCached
  selectedDocFilter.value = 'all'
  if (validateProgress.value.errors.length) {
    alert('部分文档验证失败：\n' + validateProgress.value.errors.map((e) => `${e.filename}: ${e.error}`).join('\n'))
  }
  loading.value = false
}

const loadBatch = async (force = false) => {
  if (!documentId.value) return
  loading.value = true
  try {
    const result = await getBatchDetail(documentId.value)
    batchDocuments.value = result.documents || []
  } catch (error) {
    console.error('Failed to load batch:', error)
    alert(error.response?.data?.error || error.message || '加载文件夹失败')
    loading.value = false
    return
  }
  await loadBatchValidations(force)
}

const refreshValidate = (force = true) => {
  if (isBatchMode.value) return loadBatch(force)
  return loadValidateResult(force)
}

const goToNext = () => {
  router.push({
    name: 'report',
    params: { documentId: documentId.value },
    query: withPortalQuery({
      docName: documentName.value,
      ...(isBatchMode.value ? { mode: 'batch' } : {}),
    }),
  })
}

onMounted(() => {
  if (isBatchMode.value) loadBatch(false)
  else loadValidateResult(false)
})
</script>

<style scoped>
.validation-item {
  transition: all 0.2s ease;
}

.validation-item:hover {
  transform: translateX(4px);
}

.ml-0 { margin-left: 0; }
.ml-8 { margin-left: 2rem; }
.ml-16 { margin-left: 4rem; }
.ml-24 { margin-left: 6rem; }
</style>
