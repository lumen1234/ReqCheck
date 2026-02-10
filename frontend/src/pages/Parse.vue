<template>
  <div class="parse">
    <el-card shadow="hover" style="max-width: 800px; margin: 0 auto;">
      <template #header>
        <div class="card-header">
          <span>文档解析</span>
          <el-button type="primary" @click="handleParse" :loading="loading">解析文档</el-button>
        </div>
      </template>
      <div class="card-body">
        <el-form label-width="120px">
          <el-form-item label="文档ID">
            <el-input v-model="docId" readonly></el-input>
          </el-form-item>
        </el-form>
        
        <!-- 解析结果 -->
        <el-alert
          v-if="parseError"
          :title="'解析失败: ' + parseError"
          type="error"
          show-icon
          :closable="false"
          style="margin-top: 20px;"
        ></el-alert>
        
        <!-- 需求树 -->
        <div v-if="requirementTree" style="margin-top: 20px;">
          <h3>需求树结构</h3>
          <el-tree
            :data="requirementTree.children"
            :props="treeProps"
            node-key="id"
            default-expand-all
            style="margin-top: 10px;"
          >
            <template #default="{ node, data }">
              <span class="custom-tree-node">
                <span>{{ data.name }}</span>
                <span v-if="data.original_text" class="original-text">{{ data.original_text }}</span>
              </span>
            </template>
          </el-tree>
          
          <div style="margin-top: 20px;">
            <el-button type="primary" @click="goToValidate">验证需求</el-button>
            <el-button type="success" @click="goToExport">导出需求</el-button>
            <el-button @click="goToHistory">查看历史</el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { parseDocument } from '../services/api'

export default {
  name: 'Parse',
  data() {
    return {
      docId: '',
      loading: false,
      parseError: '',
      requirementTree: null,
      treeProps: {
        children: 'children',
        label: 'name'
      }
    }
  },
  mounted() {
    // 从路由参数中获取docId
    this.docId = this.$route.params.docId
    // 自动解析
    this.handleParse()
  },
  methods: {
    async handleParse() {
      if (!this.docId) {
        this.$message.error('文档ID不能为空')
        return
      }
      
      this.loading = true
      this.parseError = ''
      this.requirementTree = null
      
      try {
        const response = await parseDocument(this.docId)
        this.requirementTree = response.data.requirement_tree
        this.$message.success('解析成功')
      } catch (error) {
        this.parseError = error.message || '解析失败，请重试'
        this.$message.error('解析失败')
      } finally {
        this.loading = false
      }
    },
    goToValidate() {
      this.$router.push(`/validate/${this.docId}`)
    },
    goToExport() {
      this.$router.push(`/export/${this.docId}`)
    },
    goToHistory() {
      this.$router.push('/history')
    }
  }
}
</script>

<style scoped>
.parse {
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

.original-text {
  margin-left: 10px;
  font-size: 12px;
  color: #999;
}
</style>
