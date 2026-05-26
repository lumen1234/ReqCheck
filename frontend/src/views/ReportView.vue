<template>
  <div class="h-full flex flex-col bg-white">
    <!-- Header -->
    <div class="border-b border-slate-200 px-8 py-6">
      <div class="max-w-7xl mx-auto">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-slate-900">文档导出</h1>
            <p class="text-slate-500 font-medium mt-2">查看和导出需求树数据</p>
          </div>
          <div class="flex items-center space-x-3">
            <button @click="exportJSON"
              class="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white font-semibold rounded-lg transition-all shadow-sm flex items-center space-x-2">
              <Download class="w-4 h-4" />
              <span>导出JSON</span>
            </button>

            <button @click="startNew"
              class="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-900 font-semibold rounded-lg transition-all flex items-center space-x-2">
              <RotateCw class="w-4 h-4" />
              <span>新建审查</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 overflow-hidden flex">
      <!-- Left: Tree View -->
      <div class="w-1/3 border-r border-slate-200 overflow-y-auto p-6">
        <RequirementTree 
          :loading="loading"
          :tree-data="treeData"
          @node-click="handleNodeClick"
        />
      </div>

      <!-- Right: Detail View -->
      <div class="flex-1 overflow-y-auto p-8">
        <div v-if="selectedNode" class="max-w-3xl space-y-6">
          <!-- Node Header -->
          <div class="space-y-2">
            <div class="flex items-center space-x-2">
              <span class="px-2 py-1 bg-primary-100 text-primary-900 text-xs font-semibold rounded">
                Level {{ selectedNode.level }}
              </span>
              <span 
                v-if="selectedNode.validation_result !== null"
                :class="getValidationStatusClass(selectedNode.validation_result)"
                class="px-2 py-1 text-xs font-semibold rounded"
              >
                {{ selectedNode.validation_result ? '✓ 验证通过' : '✗ 验证失败' }}
              </span>
            </div>
            <h2 class="text-2xl font-bold text-slate-900">{{ selectedNode.label }}</h2>
            <p class="text-xs text-slate-500 font-mono">ID: {{ selectedNode.id }}</p>
          </div>

          <!-- Node Content -->
          <div v-if="selectedNode.content" class="space-y-3">
            <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide">需求内容</h3>
            <div class="bg-slate-50 border border-slate-200 rounded-lg p-6">
              <p class="text-slate-700 leading-relaxed whitespace-pre-wrap">{{ selectedNode.content }}</p>
            </div>
          </div>

          <!-- Validation Reason -->
          <div v-if="selectedNode.validation_reason" class="space-y-3">
            <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide">验证说明</h3>
            <div 
              :class="selectedNode.validation_result ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'"
              class="border rounded-lg p-6"
            >
              <p 
                :class="selectedNode.validation_result ? 'text-green-800' : 'text-red-800'"
                class="leading-relaxed whitespace-pre-wrap"
              >{{ selectedNode.validation_reason }}</p>
            </div>
          </div>

          <!-- Children Info -->
          <div v-if="selectedNode.children && selectedNode.children.length > 0" class="space-y-3">
            <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide">子需求 ({{ selectedNode.children.length }})</h3>
            <div class="grid grid-cols-2 gap-3">
              <div 
                v-for="child in selectedNode.children" 
                :key="child.id"
                @click="selectNode(child)"
                class="p-4 bg-white border border-slate-200 rounded-lg hover:border-primary-400 hover:shadow-md transition-all cursor-pointer"
              >
                <div class="flex items-start justify-between mb-2">
                  <p class="text-sm font-semibold text-slate-900 flex-1">{{ child.label }}</p>
                  <span 
                    v-if="child.validation_result !== null"
                    :class="child.validation_result ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                    class="ml-2 text-xs px-1.5 py-0.5 rounded"
                  >
                    {{ child.validation_result ? '✓' : '✗' }}
                  </span>
                </div>
                <p class="text-xs text-slate-500">{{ child.id }}</p>
              </div>
            </div>
          </div>

          <!-- Statistics -->
          <div class="bg-slate-50 border border-slate-200 rounded-lg p-6">
            <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide mb-4">统计信息</h3>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <p class="text-xs text-slate-500 mb-1">总需求数</p>
                <p class="text-xl font-bold text-slate-900">{{ totalNodes }}</p>
              </div>
              <div>
                <p class="text-xs text-slate-500 mb-1">验证通过</p>
                <p class="text-xl font-bold text-green-600">{{ passedNodes }}</p>
              </div>
              <div>
                <p class="text-xs text-slate-500 mb-1">验证失败</p>
                <p class="text-xl font-bold text-red-600">{{ failedNodes }}</p>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="flex items-center justify-center h-full text-slate-400">
          <div class="text-center">
            <FileText class="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p class="text-sm">请从左侧选择需求节点</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { exportRequirements } from '../api'
import { Download, RotateCw, FileText } from 'lucide-vue-next'
import RequirementTree from '../components/RequirementTree.vue'

const router = useRouter()
const route = useRoute()

// 从 URL 获取参数
const documentId = computed(() => route.params.documentId)

const loading = ref(false)
const flatRequirements = ref([])
const selectedNode = ref(null)

/**
 * 将扁平的需求列表转换为树形结构
 * @param {Array} flatList - 扁平的需求列表
 * @returns {Array} 树形结构的需求列表
 */
const convertFlatToTree = (flatList) => {
  if (!flatList || flatList.length === 0) return []
  
  // 创建ID到节点的映射
  const idMap = {}
  const tree = []
  
  // 第一遍遍历：转换节点格式并建立映射
  flatList.forEach(item => {
    const node = {
      id: item.node_id || item.id,
      label: item.title || item.label,
      content: item.content || '',
      level: item.level || 0,
      validation_result: item.validation_result,
      validation_reason: item.validation_reason || '',
      children: [],
      // 保留原始数据以便后续使用
      _originalId: item.id,
      _parentId: item.parent_id
    }
    idMap[item.id] = node
  })
  
  // 第二遍遍历：建立父子关系
  flatList.forEach(item => {
    const node = idMap[item.id]
    if (item.parent_id === 'root') {
      // 根节点
      tree.push(node)
    } else if (idMap[item.parent_id]) {
      // 添加到父节点的children中
      idMap[item.parent_id].children.push(node)
    }
  })
  
  // 清理临时属性
  const cleanNode = (node) => {
    delete node._originalId
    delete node._parentId
    if (node.children && node.children.length > 0) {
      node.children.forEach(cleanNode)
    } else {
      node.children = []
    }
    return node
  }
  
  return tree.map(cleanNode)
}

// 计算属性：树形数据
const treeData = computed(() => {
  return convertFlatToTree(flatRequirements.value)
})

// JSON字符串（用于导出）
const jsonString = computed(() => {
  if (!flatRequirements.value || flatRequirements.value.length === 0) return ''
  return JSON.stringify(flatRequirements.value, null, 2)
})

// 统计节点数量
const countNodes = (nodes, filter = null) => {
  let count = 0
  const traverse = (nodeList) => {
    for (const node of nodeList) {
      if (!filter || filter(node)) {
        count++
      }
      if (node.children && node.children.length > 0) {
        traverse(node.children)
      }
    }
  }
  traverse(nodes)
  return count
}

const totalNodes = computed(() => {
  return flatRequirements.value ? flatRequirements.value.length : 0
})

const passedNodes = computed(() => {
  return flatRequirements.value 
    ? flatRequirements.value.filter(n => n.validation_result === true).length 
    : 0
})

const failedNodes = computed(() => {
  return flatRequirements.value 
    ? flatRequirements.value.filter(n => n.validation_result === false).length 
    : 0
})

// 处理节点点击事件
const handleNodeClick = (data, node, component) => {
  selectedNode.value = data
}

// 选择节点
const selectNode = (node) => {
  selectedNode.value = node
}

// 获取验证状态样式类
const getValidationStatusClass = (result) => {
  if (result === true) {
    return 'bg-green-100 text-green-800 border border-green-300'
  } else if (result === false) {
    return 'bg-red-100 text-red-800 border border-red-300'
  }
  return 'bg-slate-100 text-slate-800 border border-slate-300'
}

// 导出JSON
const exportJSON = () => {
  if (!flatRequirements.value || flatRequirements.value.length === 0) {
    alert('暂无数据可导出')
    return
  }

  try {
    const blob = new Blob([jsonString.value], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `requirements-${documentId.value || 'export'}.json`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Export failed:', error)
    alert('导出失败，请重试')
  }
}

// 开始新分析
const startNew = () => {
  router.push('/')
}

// 加载需求数据
const loadRequirements = async () => {
  if (!documentId.value) {
    console.warn('No documentId provided')
    return
  }
  
  loading.value = true
  try {
    const result = await exportRequirements(documentId.value)
    flatRequirements.value = result.requirements || []
    
    // 自动选择第一个根节点
    if (treeData.value && treeData.value.length > 0) {
      selectedNode.value = treeData.value[0]
    }
  } catch (error) {
    console.error('Failed to load requirements:', error)
    alert('加载需求数据失败，请重试')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRequirements()
})
</script>

<style scoped>
</style>
