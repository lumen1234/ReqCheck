<template>
  <div class="validate">
    <el-card shadow="hover" style="max-width: 800px; margin: 0 auto;">
      <template #header>
        <div class="card-header">
          <span>需求验证</span>
          <el-button type="primary" @click="handleValidate" :loading="loading">验证需求</el-button>
        </div>
      </template>
      <div class="card-body">
        <el-form label-width="120px">
          <el-form-item label="文档ID">
            <el-input v-model="docId" readonly></el-input>
          </el-form-item>
        </el-form>
        
        <!-- 验证结果 -->
        <el-alert
          v-if="validateError"
          :title="'验证失败: ' + validateError"
          type="error"
          show-icon
          :closable="false"
          style="margin-top: 20px;"
        ></el-alert>
        
        <!-- 验证结果列表 -->
        <div v-if="validationResults.length > 0" style="margin-top: 20px;">
          <h3>验证结果</h3>
          <el-table :data="validationResults" style="width: 100%; margin-top: 10px;">
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
          
          <div style="margin-top: 20px;">
            <el-button type="success" @click="goToExport">导出需求</el-button>
            <el-button @click="goToHistory">查看历史</el-button>
            <el-button @click="goToParse">查看需求树</el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { validateRequirements } from '../services/api'

export default {
  name: 'Validate',
  data() {
    return {
      docId: '',
      loading: false,
      validateError: '',
      validationResults: []
    }
  },
  mounted() {
    // 从路由参数中获取docId
    this.docId = this.$route.params.docId
    // 自动验证
    this.handleValidate()
  },
  methods: {
    async handleValidate() {
      if (!this.docId) {
        this.$message.error('文档ID不能为空')
        return
      }
      
      this.loading = true
      this.validateError = ''
      this.validationResults = []
      
      try {
        const response = await validateRequirements(this.docId)
        this.validationResults = response.data.validation_results
        this.$message.success('验证成功')
      } catch (error) {
        this.validateError = error.message || '验证失败，请重试'
        this.$message.error('验证失败')
      } finally {
        this.loading = false
      }
    },
    goToExport() {
      this.$router.push(`/export/${this.docId}`)
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
.validate {
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
