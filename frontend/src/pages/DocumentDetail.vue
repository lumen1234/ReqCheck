<template>
  <div class="document-detail">
    <el-card shadow="hover" style="max-width: 1000px; margin: 0 auto;">
      <template #header>
        <div class="card-header">
          <span>文档详情</span>
          <el-button @click="goToHistory">返回历史列表</el-button>
        </div>
      </template>
      <div class="card-body">
        <!-- 文档基本信息 -->
        <el-alert
          v-if="document"
          :title="'文档信息'"
          type="info"
          show-icon
          :closable="false"
          style="margin-bottom: 20px;"
        >
          <template #default>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
              <p><strong>文档ID:</strong> {{ document.id }}</p>
              <p><strong>文件名:</strong> {{ document.filename }}</p>
              <p><strong>文档类型:</strong> {{ document.file_type }}</p>
              <p><strong>上传时间:</strong> {{ formatDate(document.upload_time) }}</p>
              <p><strong>状态:</strong> <el-tag :type="getStatusType(document.status)">{{ document.status }}</el-tag></p>
            </div>
          </template>
        </el-alert>
        
        <!-- 需求树 -->
        <el-card v-if="requirementTrees.length > 0" shadow="hover" style="margin-bottom: 20px;">
          <template #header>
            <div class="sub-card-header">
              <span>需求树结构</span>
            </div>
          </template>
          <div v-for="(tree, index) in requirementTrees" :key="tree.id" style="margin-bottom: 20px;">
            <p><strong>解析时间:</strong> {{ formatDate(tree.parse_time) }}</p>
            <el-tree
              :data="tree.tree_json.children"
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
          </div>
        </el-card>
        
        <!-- 验证结果 -->
        <el-card v-if="validationResults.length > 0" shadow="hover">
          <template #header>
            <div class="sub-card-header">
              <span>验证结果</span>
            </div>
          </template>
          <div v-for="(result, index) in validationResults" :key="result.id" style="margin-bottom: 20px;">
            <p><strong>验证时间:</strong> {{ formatDate(result.validate_time) }}</p>
            <el-table :data="result.result_json" style="width: 100%; margin-top: 10px;">
              <el-table-column prop="name" label="需求名称" width="200"></el-table-column>
              <el-table-column prop="result" label="验证结果" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.result ? 'success' : 'danger'">
                    {{ row.result ? '合规' : '不合规' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="reason" label="验证依据"></el-table-column>
            </el-table>
          </div>
        </el-card>
        
        <!-- 操作按钮 -->
        <div style="margin-top: 20px;">
          <el-button type="primary" @click="goToParse">解析文档</el-button>
          <el-button type="success" @click="goToValidate">验证需求</el-button>
          <el-button type="info" @click="goToExport">导出需求</el-button>
          <el-button @click="goToHistory">返回历史</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { getDocumentDetail } from '../services/api'

export default {
  name: 'DocumentDetail',
  data() {
    return {
      docId: '',
      document: null,
      requirementTrees: [],
      validationResults: [],
      loading: false,
      treeProps: {
        children: 'children',
        label: 'name'
      }
    }
  },
  mounted() {
    this.docId = this.$route.params.docId
    this.getDocumentDetail()
  },
  methods: {
    async getDocumentDetail() {
      this.loading = true
      try {
        const response = await getDocumentDetail(this.docId)
        this.document = response.data.document
        this.requirementTrees = response.data.requirement_trees
        this.validationResults = response.data.validation_results
      } catch (error) {
        this.$message.error('获取文档详情失败')
      } finally {
        this.loading = false
      }
    },
    formatDate(dateString) {
      if (!dateString) return ''
      const date = new Date(dateString)
      return date.toLocaleString()
    },
    getStatusType(status) {
      switch (status) {
        case '已上传':
          return 'info'
        case '已解析':
          return 'success'
        default:
          return 'default'
      }
    },
    goToParse() {
      this.$router.push(`/parse/${this.docId}`)
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
.document-detail {
  padding: 40px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sub-card-header {
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
