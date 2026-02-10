<template>
  <div class="upload">
    <el-card shadow="hover" style="max-width: 600px; margin: 0 auto;">
      <template #header>
        <div class="card-header">
          <span>文档上传</span>
        </div>
      </template>
      <div class="card-body">
        <el-form label-width="120px">
          <el-form-item label="选择文件">
            <el-upload
              class="upload-demo"
              action=""
              :auto-upload="false"
              :on-change="handleFileChange"
              :show-file-list="true"
              accept=".txt,.docx"
              :limit="1"
              :on-exceed="handleExceed"
            >
              <el-button type="primary">选择文件</el-button>
              <template #tip>
                <div class="el-upload__tip">
                  请上传txt或docx格式的文件
                </div>
              </template>
            </el-upload>
          </el-form-item>
          <el-form-item label="文档类型">
            <el-select v-model="fileType" placeholder="请选择文档类型" style="width: 100%;">
              <el-option label="需求规格说明" value="需求规格说明"></el-option>
              <el-option label="其他" value="其他"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleUpload" :loading="loading">上传文档</el-button>
            <el-button @click="resetForm">重置</el-button>
          </el-form-item>
        </el-form>
        
        <!-- 上传结果 -->
        <el-alert
          v-if="uploadSuccess"
          :title="'上传成功！文档ID: ' + docId"
          type="success"
          show-icon
          :closable="false"
          style="margin-top: 20px;"
        >
          <template #default>
            <div>
              <p>文件名: {{ fileName }}</p>
              <p>文档类型: {{ fileType }}</p>
              <el-button type="primary" size="small" @click="goToParse">解析文档</el-button>
              <el-button type="success" size="small" @click="goToHistory">查看历史</el-button>
            </div>
          </template>
        </el-alert>
        
        <el-alert
          v-if="uploadError"
          :title="'上传失败: ' + uploadError"
          type="error"
          show-icon
          :closable="false"
          style="margin-top: 20px;"
        ></el-alert>
      </div>
    </el-card>
  </div>
</template>

<script>
import { uploadDocument } from '../services/api'

export default {
  name: 'Upload',
  data() {
    return {
      file: null,
      fileType: '需求规格说明',
      loading: false,
      uploadSuccess: false,
      uploadError: '',
      docId: '',
      fileName: ''
    }
  },
  methods: {
    handleFileChange(file) {
      this.file = file.raw
    },
    handleExceed() {
      this.$message.warning('只能上传一个文件')
    },
    async handleUpload() {
      if (!this.file) {
        this.$message.error('请选择文件')
        return
      }
      if (!this.fileType) {
        this.$message.error('请选择文档类型')
        return
      }
      
      this.loading = true
      this.uploadSuccess = false
      this.uploadError = ''
      
      try {
        const response = await uploadDocument(this.file, this.fileType)
        const data = response.data
        this.docId = data.doc_id
        this.fileName = data.filename
        this.uploadSuccess = true
        this.$message.success('上传成功')
      } catch (error) {
        this.uploadError = error.message || '上传失败，请重试'
        this.$message.error('上传失败')
      } finally {
        this.loading = false
      }
    },
    resetForm() {
      this.file = null
      this.fileType = '需求规格说明'
      this.uploadSuccess = false
      this.uploadError = ''
      this.docId = ''
      this.fileName = ''
    },
    goToParse() {
      this.$router.push(`/parse/${this.docId}`)
    },
    goToHistory() {
      this.$router.push('/history')
    }
  }
}
</script>

<style scoped>
.upload {
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
