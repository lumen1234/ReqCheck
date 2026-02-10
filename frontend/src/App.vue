<template>
  <div class="app">
    <el-container style="min-height: 100vh">
      <el-header height="60px" style="background-color: #1890ff; color: white; display: flex; align-items: center; justify-content: space-between;">
        <h1 style="margin: 0; font-size: 20px;">需求验证系统</h1>
        <el-menu :default-active="activeIndex" mode="horizontal" background-color="transparent" text-color="white" active-text-color="white">
          <el-menu-item index="/">
            <router-link to="/">首页</router-link>
          </el-menu-item>
          <el-menu-item index="/upload">
            <router-link to="/upload">上传文档</router-link>
          </el-menu-item>
          <el-menu-item index="/history">
            <router-link to="/history">历史记录</router-link>
          </el-menu-item>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
      <el-footer height="40px" style="text-align: center; line-height: 40px; background-color: #f0f2f5;">
        需求验证系统 ©2026
      </el-footer>
    </el-container>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      activeIndex: '/'
    }
  },
  watch: {
    $route: {
      handler() {
        this.activeIndex = this.$route.path
      },
      immediate: true
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app {
  font-family: Arial, sans-serif;
}
</style>
