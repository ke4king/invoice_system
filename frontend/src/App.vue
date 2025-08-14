<template>
  <el-config-provider>
    <router-view />
  </el-config-provider>
  </template>

<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'
</script>

<style>
#app {
  min-height: 100vh;
}
</style>