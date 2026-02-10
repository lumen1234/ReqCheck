<template>
  <div class="home">
    <el-card shadow="hover" style="max-width: 800px; margin: 0 auto;">
      <template #header>
        <div class="card-header">
          <span>需求验证系统</span>
        </div>
      </template>
      <div class="card-body">
        <h2>系统功能</h2>
        <el-divider></el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card shadow="hover" style="height: 180px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
              <el-icon class="icon"><Upload /></el-icon>
              <h3>文档上传</h3>
              <p>支持上传txt和docx格式的需求文档</p>
              <el-button type="primary" @click="$router.push('/upload')">立即上传</el-button>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover" style="height: 180px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
              <el-icon class="icon"><Document /></el-icon>
              <h3>需求解析</h3>
              <p>基于文档标题构造需求树结构</p>
              <el-button type="success" @click="$router.push('/history')">查看历史</el-button>
            </el-card>
          </el-col>
        </el-row>
        <el-row :gutter="20" style="margin-top: 20px;">
          <el-col :span="12">
            <el-card shadow="hover" style="height: 180px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
              <el-icon class="icon"><Check /></el-icon>
              <h3>需求验证</h3>
              <p>使用大模型判断需求是否合规</p>
              <el-button type="warning" @click="$router.push('/history')">查看历史</el-button>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover" style="height: 180px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
              <el-icon class="icon"><Download /></el-icon>
              <h3>需求导出</h3>
              <p>导出分条的JSON格式需求</p>
              <el-button type="info" @click="$router.push('/history')">查看历史</el-button>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'Home'
}
</script>

<style scoped>
.home {
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

.icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #1890ff;
}

.el-card {
  transition: all 0.3s ease;
}

.el-card:hover {
  transform: translateY(-5px);
}
</style>
