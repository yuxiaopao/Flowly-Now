<template>
  <div class="profile-settings">
    <h2 class="section-title">
      个人资料
    </h2>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      class="profile-form"
    >
      <div class="avatar-section">
        <el-avatar
          :size="80"
          :src="form.avatar"
        >
          {{ form.username?.[0]?.toUpperCase() }}
        </el-avatar>
        <div class="avatar-actions">
          <el-button size="small">
            上传头像
          </el-button>
          <span class="avatar-hint">支持 JPG、PNG 格式，最大 2MB</span>
        </div>
      </div>

      <el-form-item
        label="用户名"
        prop="username"
      >
        <el-input v-model="form.username" />
      </el-form-item>

      <el-form-item
        label="邮箱"
        prop="email"
      >
        <el-input
          v-model="form.email"
          type="email"
        />
      </el-form-item>

      <el-form-item
        label="姓名"
        prop="first_name"
      >
        <el-input
          v-model="form.first_name"
          placeholder="名"
        />
      </el-form-item>

      <el-form-item
        label="姓氏"
        prop="last_name"
      >
        <el-input
          v-model="form.last_name"
          placeholder="姓"
        />
      </el-form-item>

      <el-form-item
        label="个人简介"
        prop="bio"
      >
        <el-input
          v-model="form.bio"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
          placeholder="介绍一下自己..."
        />
      </el-form-item>

      <el-form-item>
        <AppButton
          variant="primary"
          :loading="isLoading"
          @click="handleSubmit"
        >
          保存更改
        </AppButton>
      </el-form-item>
    </el-form>

    <el-divider />

    <div class="security-section">
      <h3 class="subsection-title">
        修改密码
      </h3>
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-position="top"
      >
        <el-form-item
          label="当前密码"
          prop="old_password"
        >
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            show-password
          />
        </el-form-item>

        <el-form-item
          label="新密码"
          prop="new_password"
        >
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            show-password
          />
        </el-form-item>

        <el-form-item
          label="确认新密码"
          prop="new_password_confirm"
        >
          <el-input
            v-model="passwordForm.new_password_confirm"
            type="password"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <AppButton @click="handleChangePassword">
            修改密码
          </AppButton>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import AppButton from '@/components/common/AppButton.vue'

const authStore = useAuthStore()
const appStore = useAppStore()

const formRef = ref(null)
const passwordFormRef = ref(null)
const isLoading = ref(false)

const form = reactive({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  bio: '',
  avatar: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  new_password_confirm: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

const passwordRules = {
  old_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 个字符', trigger: 'blur' }
  ],
  new_password_confirm: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

onMounted(() => {
  // Load user data
  const user = authStore.user
  if (user) {
    form.username = user.username || ''
    form.email = user.email || ''
    form.first_name = user.first_name || ''
    form.last_name = user.last_name || ''
    form.bio = user.bio || ''
    form.avatar = user.avatar || ''
  }
})

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  isLoading.value = true
  try {
    await authStore.updateProfile(form)
    appStore.success('个人资料已更新')
  } catch (err) {
    appStore.error('更新失败')
  } finally {
    isLoading.value = false
  }
}

async function handleChangePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    await authStore.changePassword(passwordForm)
    appStore.success('密码修改成功')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.new_password_confirm = ''
  } catch (err) {
    appStore.error('密码修改失败')
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.section-title {
  font-size: $font-size-xl;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-6;
}

.profile-form {
  max-width: 500px;
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: $spacing-4;
  margin-bottom: $spacing-6;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.avatar-hint {
  font-size: $font-size-xs;
  color: var(--text-primary)-tertiary;
}

.subsection-title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: $spacing-6 0 $spacing-4;
}
</style>

