<template>
  <div class="history">
    <el-card shadow="hover" style="max-width: 1000px; margin: 0 auto;">
      <template #header>
        <div class="card-header">
          <span>历史记录</span>
          <el-button type="primary" @click="$router.push('/upload')">上传新文档</el-button>
        </div>
      </template>
      <div class="card-body">
        <el-table :data="documents" style="width: 100%;" :loading="loading">
          <el-table-column prop="id" label="文档ID" width="300"></el-table-column>
          <el-table-column prop="filename" label="文件名"></el-table-column>
          <el-table-column prop="file_type" label="文档类型" width="150"></el-table-column>
          <el-table-column prop="upload_time" label="上传时间" width="200">
            <template #default="{ row }">
              {{ formatDate(row.upload_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="300">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="goToParse(row.id)">解析</el-button>
              <el-button type="success" size="small" @click="goToValidate(row.id)">验证</el-button>
              <el-button type="info" size="small" @click="goToExport(row.id)">导出</el-button>
              <el-button type="warning" size="small" @click="goToDetail(row.id)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <el-pagination
          v-if="documents.length > 0"
          layout="prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="currentPage"
          @current-change="handleCurrentChange"
          style="margin-top: 20px; text-align: right;"
        ></el-pagination>
        
        <el-empty
          v-if="!loading && documents.length === 0"
          description="暂无文档记录"
          style="margin: 40px 0;"
        >
          <el-button type="primary" @click="$router.push('/upload')">上传文档</el-button>
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script>
import { getDocuments } from '../services/api'

export default {
  name: 'History',
  data() {
    return {
      documents: [],
      loading: false,
      total: 0,
      currentPage: 1,
      pageSize: 10
    }
  },
  mounted() {
    this.getDocumentList()
  },
  methods: {
    async getDocumentList() {
      this.loading = true
      try {
        const response = await getDocuments()
        this.documents = response.data.documents
        this.total = this.documents.length
      } catch (error) {
        this.$message.error('获取文档列表失败')
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
    handleCurrentChange(page) {
      this.currentPage = page
      // 实际项目中这里应该调用分页接口
    },
    goToParse(docId) {
      this.$router.push(`/parse/${docId}`)
    },
    goToValidate(docId) {
      this.$router.push(`/validate/${docId}`)
    },
    goToExport(docId) {
      this.$router.push(`/export/${docId}`)
    },
    goToDetail(docId) {
      this.$router.push(`/document/${docId}`)
    }
  }
}
</script>

<style scoped>
.history {
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
