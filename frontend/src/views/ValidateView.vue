<template>
  <div class="h-full flex flex-col bg-white">
    <!-- Header -->
    <div class="border-b border-slate-200 px-8 py-6">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-slate-900">需求验证</h1>
          <p class="text-slate-500 font-medium mt-2">审查软件需求文档完整性与准确性</p>
        </div>
        
        <!-- Statistics -->
        <div v-if="validationData.length > 0" class="flex items-center space-x-4">
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
        </div>
      </div>
    </div>

    <!-- Main Content - List View -->
    <div class="flex-1 overflow-y-auto p-8">
      <div class="max-w-7xl mx-auto">
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-12">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p class="text-slate-600 mt-4">加载验证结果...</p>
        </div>

        <!-- Empty State -->
        <div v-else-if="validationData.length === 0" class="text-center py-12">
          <FileText class="w-16 h-16 mx-auto mb-4 text-slate-300" />
          <p class="text-slate-500 mb-4">暂无验证数据</p>
          <button 
            @click="loadValidateResult(false)"
            class="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white text-sm font-semibold rounded-lg transition-all"
          >
            重新加载
          </button>
          <button 
            @click="loadValidateResult(true)"
            class="ml-2 px-4 py-2 bg-slate-600 hover:bg-slate-700 text-white text-sm font-semibold rounded-lg transition-all"
          >
            强制重新验证
          </button>
        </div>

        <!-- Validation Results List -->
        <div v-else class="space-y-3">
          <div 
            v-for="(item, index) in sortedValidationData" 
            :key="item.id"
            class="validation-item bg-white border rounded-lg transition-all hover:shadow-md"
            :class="[
              item.result ? 'border-green-200 hover:border-green-300' : 'border-red-200 hover:border-red-300',
              { 'ml-0': item.level === 0, 'ml-8': item.level === 1, 'ml-16': item.level === 2, 'ml-24': item.level === 3 }
            ]"
          >
            <div class="p-4">
              <div class="flex items-start justify-between">
                <!-- Left: Node Info -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center space-x-3 mb-2">
                    <!-- Status Icon -->
                    <div 
                      class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                      :class="item.result ? 'bg-green-100' : 'bg-red-100'"
                    >
                      <CheckCircle v-if="item.result" class="w-4 h-4 text-green-600" />
                      <XCircle v-else class="w-4 h-4 text-red-600" />
                    </div>
                    
                    <!-- Node Name -->
                    <h3 class="text-base font-bold text-slate-900 truncate">
                      {{ item.name }}
                    </h3>
                    
                    <!-- Level Badge -->
                    <span class="flex-shrink-0 px-2 py-0.5 bg-slate-100 text-slate-600 text-xs font-medium rounded">
                      L{{ item.level }}
                    </span>
                  </div>
                  
                  <!-- Reason -->
                  <div class="ml-9">
                    <p class="text-sm text-slate-600 leading-relaxed">
                      {{ item.reason }}
                    </p>
                    
                    <!-- Node ID -->
                    <p class="text-xs text-slate-400 font-mono mt-1">
                      ID: {{ item.id }}
                    </p>
                  </div>
                </div>
                
                <!-- Right: Status Badge -->
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

    <!-- Bottom Action Bar -->
    <div class="border-t border-slate-200 px-8 py-4 bg-slate-50">
      <div class="max-w-7xl mx-auto flex justify-end">
        <button 
          @click="goToNext"
          :disabled="validationData.length === 0"
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
import { getReviewResult } from '../api'
import { withPortalQuery } from '../utils/portal'
import { FileText, ChevronRight, CheckCircle, XCircle } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

// 从 URL 获取参数
const documentId = computed(() => route.params.documentId)
const documentName = computed(() => route.query.docName || '未命名文档')

const loading = ref(false)
const validationData = ref([])

// 计算节点层级
const calculateLevel = (nodeId, parentId, allNodes) => {
  // 根节点
  if (!parentId || parentId === '' || parentId === null || nodeId === 'root') {
    return 0
  }
  
  // 查找父节点
  const parent = allNodes.find(n => n.id === parentId)
  if (!parent) {
    return 1 // 如果找不到父节点，默认为第一层
  }
  
  // 递归计算父节点层级
  return 1 + calculateLevel(parent.id, parent.parent_id, allNodes)
}

// 处理后端返回的数据，添加层级信息
const processValidationData = (data) => {
  if (!data || !Array.isArray(data)) {
    return []
  }
  
  // 为每个节点计算层级
  return data.map(node => ({
    ...node,
    level: calculateLevel(node.id, node.parent_id, data)
  }))
}

// 排序：按照原始顺序（通常后端已经按照文档顺序返回）
const sortedValidationData = computed(() => {
  return validationData.value
})

// 统计信息
const totalCount = computed(() => validationData.value.length)

const passedCount = computed(() => {
  return validationData.value.filter(item => item.result === true).length
})

const failedCount = computed(() => {
  return validationData.value.filter(item => item.result === false).length
})

const passRate = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((passedCount.value / totalCount.value) * 100)
})

// 跳转到下一步
const goToNext = () => {
  router.push({
    name: 'report',
    params: { documentId: documentId.value },
    query: withPortalQuery({ docName: documentName.value }),
  })
}

// 加载验证结果
const loadValidateResult = async (force = false) => {
  if (!documentId.value) {
    console.warn('documentId is missing, cannot load validation result')
    return
  }
  
  loading.value = true
  try {
    const result = await getReviewResult(
      documentId.value,
      force ? { force: 1 } : {}
    )
    
    // 处理后端返回的数据格式
    // 后端返回格式: { validation_results: [...] }
    const rawData = result.validation_results || result
    
    if (Array.isArray(rawData)) {
      validationData.value = processValidationData(rawData)
      console.log(`成功加载 ${validationData.value.length} 个验证结果`)
    } else {
      console.error('Unexpected data format:', result)
      validationData.value = []
    }
  } catch (error) {
    console.error('Failed to load validate result:', error)
    // 如果是开发环境，可以加载示例数据
    if (import.meta.env.DEV) {
      console.log('开发模式：加载示例数据')
      loadMockData()
    }
  } finally {
    loading.value = false
  }
}

// 加载示例数据（用于测试）
const loadMockData = () => {
  const mockData = [
    {
      "id": "root",
      "name": "MEMS陀螺软件需求规格说明",
      "parent_id": null,
      "reason": "根节点，无对应规范要求。",
      "result": true
    },
    {
      "id": "node_1",
      "name": "1. 范围",
      "parent_id": "",
      "reason": "无对应规范，默认合规",
      "result": true
    },
    {
      "id": "node_1_1",
      "name": "1.1. 标识",
      "parent_id": "node_1",
      "reason": "无对应规范，默认合规",
      "result": true
    },
    {
      "id": "node_1_2",
      "name": "1.2. 系统概述",
      "parent_id": "node_1",
      "reason": "文档内容存在信息缺失，不符合文档完整性要求。",
      "result": false
    },
    {
      "id": "node_2",
      "name": "2. 引用文档",
      "parent_id": "",
      "reason": "引用文档未列出具体内容，不符合引用文档章节的完整性要求。",
      "result": false
    },
    {
      "id": "node_3",
      "name": "3. 需求",
      "parent_id": "",
      "reason": "无对应规范，默认合规",
      "result": true
    },
    {
      "id": "node_3_1",
      "name": "3.1. 要求的状态和方式",
      "parent_id": "node_3",
      "reason": "无对应规范，默认合规",
      "result": true
    },
    {
      "id": "node_3_2",
      "name": "3.2. 能力需求",
      "parent_id": "node_3",
      "reason": "无对应规范，默认合规",
      "result": true
    }
  ]
  
  validationData.value = processValidationData(mockData)
}

onMounted(() => {
  loadValidateResult()
})
</script>

<style scoped>
.validation-item {
  transition: all 0.2s ease;
}

.validation-item:hover {
  transform: translateX(4px);
}

/* 层级缩进效果 */
.ml-0 {
  margin-left: 0;
}

.ml-8 {
  margin-left: 2rem;
}

.ml-16 {
  margin-left: 4rem;
}

.ml-24 {
  margin-left: 6rem;
}
</style>
