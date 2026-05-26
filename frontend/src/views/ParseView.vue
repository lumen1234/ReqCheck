<template>
  <div class="h-full flex flex-col bg-white">
    <!-- Header -->
    <div class="border-b border-slate-200 px-8 py-6">
      <div class="max-w-7xl mx-auto">
        <h1 class="text-3xl font-bold text-slate-900">文档分析</h1>
        <p class="text-slate-500 font-medium mt-2">解析文档并提取需求结构树</p>
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
          @load-mock-data="loadMockData"
        />
      </div>

      <!-- Right: Detail View -->
      <div class="flex-1 overflow-y-auto p-8">
        <div v-if="selectedNode" :key="selectedNode.id" class="max-w-3xl space-y-6">
          <!-- Node Header -->
          <div class="space-y-2">
            <div class="flex items-center space-x-2">
              <span class="px-2 py-1 bg-primary-100 text-primary-900 text-xs font-semibold rounded">
                Level {{ selectedNode.level }}
              </span>
            </div>
            <h2 class="text-2xl font-bold text-slate-900">{{ selectedNode.label }}</h2>
            <p class="text-xs text-slate-500 font-mono">ID: {{ selectedNode.id }}</p>
          </div>

          <!-- Node Content -->
          <div v-if="hasNodeContent(selectedNode)" class="space-y-3">
            <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide">需求内容</h3>
            <div class="bg-slate-50 border border-slate-200 rounded-lg p-6 space-y-4">
              <!-- 图片优先展示（避免 buried 在表格后） -->
              <div v-if="selectedNode.images && selectedNode.images.length" class="space-y-4">
                <figure
                  v-for="img in selectedNode.images"
                  :key="img.id"
                  class="text-center"
                >
                  <img
                    :key="`${selectedNode.id}-${img.id}`"
                    :src="`${img.path}?doc=${documentId}`"
                    :alt="img.caption || img.alt || '图片'"
                    class="max-w-full mx-auto border border-slate-200 rounded-lg bg-white min-h-[80px]"
                    loading="eager"
                    decoding="async"
                    @error="onImageError($event, img)"
                  />
                  <figcaption v-if="img.caption || img.alt" class="text-xs text-slate-500 mt-2">
                    {{ img.caption || img.alt }}
                  </figcaption>
                </figure>
              </div>
              <div
                v-if="selectedNode.content_html"
                class="parse-content prose prose-sm max-w-none text-slate-700"
                v-html="selectedNode.content_html"
              />
              <div v-else-if="selectedNode.tables && selectedNode.tables.length" class="space-y-4">
                <div
                  v-for="tbl in selectedNode.tables"
                  :key="tbl.id || tbl.caption"
                  class="overflow-x-auto"
                  v-html="tableToHtml(tbl)"
                />
              </div>
              <p
                v-else-if="selectedNode.content"
                class="text-slate-700 leading-relaxed whitespace-pre-wrap"
              >{{ selectedNode.content }}</p>
            </div>
          </div>

          <!-- Children Info -->
          <div v-if="selectedNode.children && selectedNode.children.length > 0" class="space-y-3">
            <h3 class="text-sm font-bold text-slate-700 uppercase tracking-wide">子需求</h3>
            <div class="grid grid-cols-2 gap-3">
              <div 
                v-for="child in selectedNode.children" 
                :key="child.id"
                @click="selectNode(child)"
                class="p-4 bg-white border border-slate-200 rounded-lg hover:border-primary-400 hover:shadow-md transition-all cursor-pointer"
              >
                <p class="text-sm font-semibold text-slate-900 mb-1">{{ child.label }}</p>
                <p class="text-xs text-slate-500">{{ child.id }}</p>
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

    <!-- Bottom Action Bar -->
    <div class="border-t border-slate-200 px-8 py-4 bg-slate-50">
      <div class="max-w-7xl mx-auto flex justify-end">
        <button 
          @click="goToNext"
          class="px-6 py-2.5 bg-primary-900 hover:bg-primary-800 text-white font-bold rounded-lg transition-all shadow-sm flex items-center space-x-2"
        >
          <span>进入需求验证</span>
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getParseResult } from '../api'
import { FileText, ChevronRight } from 'lucide-vue-next'
import RequirementTree from '../components/RequirementTree.vue'
import { withPortalQuery } from '../utils/portal'

const router = useRouter()
const route = useRoute()

const documentId = computed(() => route.params.documentId)
const documentName = computed(() => route.query.docName || '未命名文档')

const loading = ref(false)
const requirementTree = ref(null)
const selectedNode = ref(null)

const transformNode = (node) => {
  const transformed = {
    id: node.id,
    label: node.display_title || node.label || '未命名节点',
    content: node.content ?? '',
    content_html: node.content_html ?? '',
    display_title: node.display_title,
    number: node.number,
    level: node.level || 1,
    v_status: node.v_status ?? '',
    e_status: node.e_status ?? '',
    tables: node.tables,
    images: node.images,
    children: [],
  }

  if (node.children && Array.isArray(node.children) && node.children.length > 0) {
    transformed.children = node.children.map((child) => transformNode(child))
  }

  return transformed
}

const convertToTreeData = (jsonData) => {
  if (!jsonData || !Array.isArray(jsonData)) {
    return []
  }
  return jsonData.map((node) => transformNode(node))
}

const pickFirstWithContent = (nodes) => {
  for (const node of nodes || []) {
    if (hasNodeContent(node)) {
      return node
    }
    if (node.children?.length) {
      const found = pickFirstWithContent(node.children)
      if (found) return found
    }
  }
  return nodes?.[0] ?? null
}

const hasNodeContent = (node) => {
  if (!node) return false
  return Boolean(
    node.content ||
    node.content_html ||
    (node.images && node.images.length) ||
    (node.tables && node.tables.length)
  )
}

const escapeHtml = (text) => {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const tableToHtml = (table) => {
  const headers = table?.headers || []
  const rows = table?.rows || []
  if (!headers.length && !rows.length) return ''
  let html = '<table class="req-table" border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">'
  if (headers.length) {
    html += '<thead><tr>'
    headers.forEach((h) => {
      html += `<th style="border:1px solid #ccc;padding:6px;background:#f5f5f5">${escapeHtml(h)}</th>`
    })
    html += '</tr></thead>'
  }
  if (rows.length) {
    html += '<tbody>'
    rows.forEach((row) => {
      html += '<tr>'
      row.forEach((cell) => {
        html += `<td style="border:1px solid #ccc;padding:6px">${escapeHtml(cell)}</td>`
      })
      html += '</tr>'
    })
    html += '</tbody>'
  }
  html += '</table>'
  return html
}

const treeData = computed(() => convertToTreeData(requirementTree.value))

const selectNode = (node) => {
  selectedNode.value = node ? { ...node } : null
}

const handleNodeClick = (data) => {
  selectNode(data)
}

const onImageError = (event, img) => {
  console.warn('图片加载失败，请删除文档后重新上传或强制重新解析:', img?.path)
  const el = event?.target
  if (el) {
    el.alt = '图片无法显示（请重新解析文档）'
    el.classList.add('opacity-50')
  }
}

const selectInitialNode = () => {
  const first = pickFirstWithContent(treeData.value)
  selectNode(first)
}

const loadMockData = () => {
  requirementTree.value = [
    {
      id: 'req-1',
      label: '1. 系统概述',
      content: '本系统是一个文档审查工具，用于分析和审查软件需求文档。',
      level: 1,
      v_status: true,
      e_status: 'pass',
      children: [
        {
          id: 'req-1-1',
          label: '1.1 系统目标',
          content: '提供自动化的文档审查能力，提高文档质量。',
          level: 2,
          v_status: true,
          e_status: 'pass',
          children: [],
        },
        {
          id: 'req-1-2',
          label: '1.2 应用范围',
          content: '适用于软件开发过程中的需求文档审查。',
          level: 2,
          v_status: true,
          e_status: 'pending',
          children: [],
        },
      ],
    },
    {
      id: 'req-2',
      label: '2. 功能需求',
      content: '系统应提供以下功能模块。',
      level: 1,
      v_status: true,
      e_status: 'pass',
      children: [
        {
          id: 'req-2-1',
          label: '2.1 文档上传',
          content: '用户可以上传Word、PDF等格式的文档。',
          level: 2,
          v_status: true,
          e_status: 'pass',
          children: [
            {
              id: 'req-2-1-1',
              label: '2.1.1 支持的格式',
              content: '系统应支持.docx, .pdf, .txt格式的文档上传。',
              level: 3,
              v_status: true,
              e_status: 'pass',
              children: [],
            },
            {
              id: 'req-2-1-2',
              label: '2.1.2 文件大小限制',
              content: '单个文件大小不超过50MB。',
              level: 3,
              v_status: false,
              e_status: 'fail',
              children: [],
            },
          ],
        },
        {
          id: 'req-2-2',
          label: '2.2 需求分析',
          content: '系统自动解析文档并提取需求结构。',
          level: 2,
          v_status: true,
          e_status: 'pending',
          children: [],
        },
        {
          id: 'req-2-3',
          label: '2.3 需求补全',
          content: '对缺失或不完整的需求进行分析和建议。',
          level: 2,
          v_status: false,
          e_status: 'pending',
          children: [],
        },
      ],
    },
    {
      id: 'req-3',
      label: '3. 非功能需求',
      content: '系统的性能、安全等非功能性要求。',
      level: 1,
      v_status: true,
      e_status: 'pass',
      children: [
        {
          id: 'req-3-1',
          label: '3.1 性能需求',
          content: '系统响应时间应在3秒以内。',
          level: 2,
          v_status: true,
          e_status: 'pass',
          children: [],
        },
        {
          id: 'req-3-2',
          label: '3.2 安全需求',
          content: '用户数据应加密存储和传输。',
          level: 2,
          v_status: true,
          e_status: 'pass',
          children: [],
        },
      ],
    },
  ]

  selectInitialNode()
}

const goToNext = () => {
  router.push({
    name: 'validate',
    params: { documentId: documentId.value },
    query: withPortalQuery({ docName: documentName.value }),
  })
}

const loadRequirementTree = async () => {
  if (!documentId.value) return

  loading.value = true
  try {
    const result = await getParseResult(documentId.value)
    requirementTree.value = result.requirement_tree.children || null
    selectInitialNode()
  } catch (error) {
    console.error('Failed to load requirement tree:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRequirementTree()
})
</script>

<style scoped>
.parse-content :deep(.req-table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  display: table;
}
.parse-content :deep(.req-table th),
.parse-content :deep(.req-table td) {
  border: 1px solid #ccc;
  padding: 6px;
  vertical-align: top;
}
.parse-content :deep(.req-table th) {
  background: #f5f5f5;
}
</style>
