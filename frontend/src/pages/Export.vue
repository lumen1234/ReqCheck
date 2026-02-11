<template>
  <div class="export">
    <el-card shadow="hover" style="max-width: 800px; margin: 0 auto;">
      <template #header>
        <div class="card-header">
          <span>需求导出</span>
          <el-button type="primary" @click="handleExport" :loading="loading">导出需求</el-button>
        </div>
      </template>
      <div class="card-body">
        <el-form label-width="120px">
          <el-form-item label="文档ID">
            <el-input v-model="docId" readonly></el-input>
          </el-form-item>
        </el-form>
        
        <!-- 导出结果 -->
        <el-alert
          v-if="exportError"
          :title="'导出失败: ' + exportError"
          type="error"
          show-icon
          :closable="false"
          style="margin-top: 20px;"
        ></el-alert>
        
        <!-- 导出结果 -->
        <div v-if="exportSuccess" style="margin-top: 20px;">
          <el-alert
            :title="'导出成功！文件名: ' + exportFile"
            type="success"
            show-icon
            :closable="false"
          ></el-alert>
          
          <h3 style="margin-top: 20px;">需求树结构</h3>
          <el-tree
            :data="requirements.children"
            :props="treeProps"
            node-key="id"
            default-expand-all
            style="margin-top: 10px;"
          >
            <template #default="{ node, data }">
              <span class="custom-tree-node">
                <span>{{ data.label }}</span>
                <span v-if="data.content" class="original-text">{{ data.content }}</span>
              </span>
            </template>
          </el-tree>
          
          <div style="margin-top: 20px;">
            <el-button type="primary" @click="downloadJson">下载JSON文件</el-button>
            <el-button @click="goToHistory">查看历史</el-button>
            <el-button @click="goToParse">查看需求树</el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { exportRequirements } from '../services/api'

export default {
  name: 'Export',
  data() {
    return {
      docId: '',
      loading: false,
      exportError: '',
      exportSuccess: false,
      exportFile: '',
      requirements: {},
      treeProps: {
        children: 'children',
        label: 'label'
      }
    }
  },
  mounted() {
    // 从路由参数中获取docId
    this.docId = this.$route.params.docId
    // 自动导出
    this.handleExport()
  },
  methods: {
    async handleExport() {
      if (!this.docId) {
        this.$message.error('文档ID不能为空')
        return
      }
      
      this.loading = true
      this.exportError = ''
      this.exportSuccess = false
      this.exportFile = ''
      this.requirements = []
      
      try {
        const response = await exportRequirements(this.docId)
        this.exportFile = response.data.export_file
        this.requirements = response.data.requirements
        this.exportSuccess = true
        this.$message.success('导出成功')
      } catch (error) {
        this.exportError = error.message || '导出失败，请重试'
        this.$message.error('导出失败')
      } finally {
        this.loading = false
      }
    },
    downloadJson() {
      // 创建JSON文件并下载
      const jsonContent = JSON.stringify(this.requirements, null, 2)
      const blob = new Blob([jsonContent], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = this.exportFile || `requirements_${this.docId}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
    goToHistory() {
      this.$router.push('/history')
    },
    goToParse() {
      this.$router.push(`/parse/${this.docId}`)
    }
  }
}
</script>

<style scoped>
.export {
  padding: 40px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-body {
  padding: 20px;
}
</style>
