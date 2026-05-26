<template>
  <nav class="bg-white border-b border-slate-200 px-6 py-4">
    <div class="max-w-7xl mx-auto flex items-center justify-between">
      <!-- Logo 区域 -->
      <div class="flex items-center space-x-2">
        <div class="w-8 h-8 bg-primary-900 rounded flex items-center justify-center">
          <span class="font-bold text-white">D</span>
        </div>
        <span class="text-lg font-bold tracking-tight text-slate-900">Doc Review</span>
      </div>

      <!-- 步骤导航 -->
      <div class="flex items-center space-x-4">
        <template v-for="(step, index) in steps" :key="step.routeName">
          <div class="flex items-center">
            <!-- 连接线 -->
            <div v-if="index > 0" class="h-px w-8 mx-2" :class="getConnectorClass(index)"></div>
            
            <!-- 步骤项 -->
            <div
              :class="getStepClass(index)"
              @click="handleStepClick(index, step)"
              class="flex items-center space-x-2 px-3 py-1.5 rounded-full transition-all duration-200"
            >
              <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold" :class="getIconClass(index)">
                <component :is="CheckIcon" class="w-4 h-4" v-if="isCompleted(index)" />
                <span v-else>{{ index + 1 }}</span>
              </div>
              <span class="text-sm font-semibold">{{ step.name }}</span>
            </div>
          </div>
        </template>
      </div>

      <!-- 右侧信息区 -->
      <div class="flex items-center space-x-4 text-xs text-slate-500">
        <div v-if="documentName" class="flex items-center bg-slate-100 px-3 py-1 rounded-full">
          <span class="opacity-60 mr-2 font-medium">Document:</span>
          <span class="text-slate-900 font-semibold">{{ documentName }}</span>
        </div>
        <!-- LLM 配置按钮 -->
        <button
          @click="showLLMSettings = true"
          class="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-800"
          title="LLM 配置"
        >
          <Settings class="w-5 h-5" />
        </button>
      </div>

      <!-- LLM 配置弹窗 -->
      <ModelSetting
        :visible="showLLMSettings"
        @close="showLLMSettings = false"
        @saved="showLLMSettings = false"
      />
    </div>
  </nav>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, Upload, FileText, FileCheck, Settings } from 'lucide-vue-next'
import ModelSetting from '@/components/ModelSetting.vue'
import { withPortalQuery } from '@/utils/portal'

const showLLMSettings = ref(false)

const route = useRoute()
const router = useRouter()

const CheckIcon = Check

// 步骤定义 - 根据文档审查流程定制
const steps = [
  { name: '文档上传', routeName: 'upload', icon: Upload },
  { name: '文档分析', routeName: 'parse', icon: FileText },
  { name: '需求验证', routeName: 'validate', icon: FileCheck },
  { name: '文档导出', routeName: 'report', icon: FileCheck },
]

// 从路由中获取状态信息
const documentId = computed(() => route.params.documentId || null)
const documentName = computed(() => route.query.docName || null)

// 当前步骤索引
const currentStepIndex = computed(() => {
  const routeName = route.name
  if (routeName === 'upload') return 0
  if (routeName === 'parse') return 1
  if (routeName === 'validate') return 2
  if (routeName === 'report') return 3
  return 0
})

// 判断步骤是否已完成
const isCompleted = (index) => {
  // 只有文档上传后，才能进入后续步骤
  if (index === 0) return documentId.value !== null && currentStepIndex.value > 0
  // 已经进入过的步骤被标记为完成
  return currentStepIndex.value > index
}

// 判断步骤是否为当前激活步骤
const isActive = (index) => currentStepIndex.value === index

// 判断步骤是否禁用
const isDisabled = (index) => {
  // 上传步骤始终可用
  if (index === 0) return false
  // 其他步骤需要有 documentId
  return documentId.value === null
}

// 获取步骤样式类
const getStepClass = (index) => {
  if (isActive(index)) return 'bg-primary-900 text-white shadow-md cursor-default'
  if (isCompleted(index)) return 'text-green-600 hover:bg-green-50 cursor-pointer'
  if (isDisabled(index)) return 'text-slate-300 cursor-not-allowed'
  return 'text-slate-600 hover:bg-slate-100 cursor-pointer'
}

// 获取图标样式类
const getIconClass = (index) => {
  if (isActive(index)) return 'bg-white text-primary-900'
  if (isCompleted(index)) return 'bg-green-500 text-white'
  if (isDisabled(index)) return 'bg-slate-100 text-slate-300'
  return 'bg-slate-200 text-slate-600'
}

// 获取连接线样式类
const getConnectorClass = (index) => {
  if (index <= currentStepIndex.value) return 'bg-primary-900'
  return 'bg-slate-200'
}

// 处理步骤点击
const handleStepClick = (index, step) => {
  if (isDisabled(index)) return
  
  // 构建路由参数
  const routeConfig = { name: step.routeName }
  
  // 如果不是上传步骤，需要带上 documentId
  if (step.routeName !== 'upload' && documentId.value) {
    routeConfig.params = { documentId: documentId.value }
    if (documentName.value) {
      routeConfig.query = withPortalQuery({ docName: documentName.value })
    }
  }
  
  router.push(routeConfig)
}
</script>
