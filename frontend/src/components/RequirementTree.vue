<template>
  <div class="requirement-tree-container space-y-2">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
      <p class="text-sm text-slate-600 mt-3">加载需求树...</p>
    </div>
    
    <!-- Tree View -->
    <div v-else-if="treeData && treeData.length > 0" class="requirement-tree">
      <el-tree
        :data="treeData"
        :props="treeProps"
        node-key="id"
        :default-expand-all="true"
        :highlight-current="true"
        @node-click="handleNodeClick"
        class="custom-tree"
      >
        <template #default="{ node, data }">
          <span class="custom-tree-node">
            <span class="node-label">{{ data.label }}</span>
          </span>
        </template>
      </el-tree>
    </div>
    
    <!-- Empty State -->
    <div v-else class="text-center py-8 text-slate-400">
      <FileText class="w-12 h-12 mx-auto mb-3 opacity-50" />
      <p class="text-sm">暂无需求数据</p>
      <button 
        @click="handleLoadMockData"
        class="mt-4 px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white text-sm font-semibold rounded-lg transition-all"
      >
        加载示例数据
      </button>
    </div>
  </div>
</template>

<script setup>
import { ElTree } from 'element-plus'
import { FileText } from 'lucide-vue-next'
import 'element-plus/dist/index.css'

// Props
defineProps({
  loading: {
    type: Boolean,
    default: false
  },
  treeData: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['node-click', 'load-mock-data'])

// Element Plus Tree 的配置
const treeProps = {
  children: 'children',
  label: 'label',
}

// 处理节点点击事件
const handleNodeClick = (data, node, component) => {
  emit('node-click', data, node, component)
}

// 处理加载示例数据
const handleLoadMockData = () => {
  emit('load-mock-data')
}
</script>

<style scoped>
/* Element Plus Tree 自定义样式 */
.requirement-tree :deep(.el-tree) {
  background: transparent;
  color: #334155;
}

.requirement-tree :deep(.el-tree-node__content) {
  height: auto;
  min-height: 32px;
  padding: 4px 0;
  border-radius: 6px;
  transition: all 0.2s;
}

.requirement-tree :deep(.el-tree-node__content:hover) {
  background-color: #f1f5f9;
}

.requirement-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background-color: #0f172a !important;
  color: white;
}

/* 只针对当前节点本身，不影响子节点 */
.requirement-tree :deep(.el-tree-node.is-current > .el-tree-node__content .custom-tree-node) {
  color: white;
}

/* 选中时勋章保持深色调填充 */
.requirement-tree :deep(.el-tree-node.is-current > .el-tree-node__content .badge-green) {
  background-color: #166534;
  border-color: #166534;
  color: white;
}

.requirement-tree :deep(.el-tree-node.is-current > .el-tree-node__content .badge-yellow) {
  background-color: #854d0e;
  border-color: #854d0e;
  color: white;
}

.requirement-tree :deep(.el-tree-node.is-current > .el-tree-node__content .badge-red) {
  background-color: #991b1b;
  border-color: #991b1b;
  color: white;
}

.requirement-tree :deep(.el-tree-node.is-current > .el-tree-node__content .badge-gray) {
  background-color: #475569;
  border-color: #475569;
  color: white;
}

.requirement-tree :deep(.el-tree-node__expand-icon) {
  font-size: 14px;
  color: #64748b;
}

/* 只针对当前节点的展开图标，不影响子节点 */
.requirement-tree :deep(.el-tree-node.is-current > .el-tree-node__content .el-tree-node__expand-icon) {
  color: white;
}

/* 自定义树节点样式 */
.custom-tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;
}

.node-label {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-badges {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}

.badge {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  border: 1px solid;
}

.badge-green {
  background-color: #dcfce7;
  border-color: #86efac;
  color: #166534;
}

.badge-yellow {
  background-color: #fef3c7;
  border-color: #fde047;
  color: #854d0e;
}

.badge-red {
  background-color: #fee2e2;
  border-color: #fca5a5;
  color: #991b1b;
}

.badge-gray {
  background-color: #f1f5f9;
  border-color: #cbd5e1;
  color: #475569;
}
</style>
