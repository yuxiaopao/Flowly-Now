<template>
  <div class="profile-settings">
    <PageHeader
      compact
      :title="copy.title"
      :subtitle="copy.subtitle"
    />
    <el-skeleton
      v-if="isFetching"
      :rows="limits.bioRows"
      animated
    />
    <el-alert
      v-else-if="loadError"
      :title="loadError"
      type="error"
      :closable="false"
      show-icon
    >
      <AppButton
        variant="secondary"
        @click="loadProfile"
      >
        {{ copy.retry }}
      </AppButton>
    </el-alert>
    <div
      v-else
      class="profile-columns"
    >
      <section
        class="profile-section"
        aria-labelledby="profile-details-title"
      >
        <div class="section-heading">
          <h2 id="profile-details-title">
            {{ copy.basicTitle }}
          </h2>
        </div>
        <div class="profile-identity">
          <AccountAvatar :size="limits.avatarSize" />
          <div class="identity-details">
            <strong>{{ copy.avatarLabel }}</strong>
            <p class="field-hint">
              {{ copy.avatarHint }}
            </p>
            <p
              v-if="avatarError"
              class="inline-error"
              role="alert"
            >
              {{ avatarError }}
            </p>
          </div>
          <div class="avatar-actions">
            <AppButton
              v-if="avatarIsImage || authStore.user?.avatar"
              variant="ghost"
              size="small"
              :disabled="isUploading || isSaving"
              @click="switchAvatarMode"
            >
              {{ avatarIsImage ? ACCOUNT_AVATAR.chooseRobot : ACCOUNT_AVATAR.chooseImage }}
            </AppButton>
            <AppButton
              variant="secondary"
              size="small"
              :disabled="isUploading || isSaving"
              @click="router.push(studio.route)"
            >
              <Sparkles aria-hidden="true" />{{ copy.designAvatar }}
            </AppButton>
            <AppButton
              variant="secondary"
              size="small"
              :loading="isUploading"
              :disabled="isSaving"
              @click="avatarInput?.click()"
            >
              <Upload aria-hidden="true" />{{ copy.upload }}
            </AppButton>
            <AppButton
              v-if="authStore.user?.avatar"
              variant="ghost"
              size="small"
              :disabled="isUploading || isSaving"
              @click="removeAvatar"
            >
              {{ copy.remove }}
            </AppButton>
          </div>
          <input
            ref="avatarInput"
            class="avatar-input"
            type="file"
            :accept="limits.avatarAccept"
            :aria-label="copy.upload"
            @change="uploadAvatar"
          >
        </div>
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          :disabled="isSaving"
          @submit.prevent="handleSubmit"
        >
          <div class="profile-fields">
            <el-form-item
              :label="copy.username"
              prop="username"
              :error="profileErrors.username"
            >
              <el-input
                v-model="form.username"
                :maxlength="limits.username"
                autocomplete="username"
                @input="profileErrors.username = ''"
              />
              <span class="field-hint">{{ copy.usernameHint }}</span>
            </el-form-item>
            <el-form-item
              :label="copy.email"
              prop="email"
              :error="profileErrors.email"
            >
              <el-input
                v-model="form.email"
                type="email"
                :maxlength="limits.email"
                autocomplete="email"
                @input="profileErrors.email = ''"
              />
            </el-form-item>
            <div class="name-fields">
              <el-form-item
                :label="copy.lastName"
                prop="lastName"
                :error="profileErrors.lastName"
              >
                <el-input
                  v-model="form.lastName"
                  :maxlength="limits.name"
                  autocomplete="family-name"
                  @input="profileErrors.lastName = ''"
                />
              </el-form-item>
              <el-form-item
                :label="copy.firstName"
                prop="firstName"
                :error="profileErrors.firstName"
              >
                <el-input
                  v-model="form.firstName"
                  :maxlength="limits.name"
                  autocomplete="given-name"
                  @input="profileErrors.firstName = ''"
                />
              </el-form-item>
            </div>
            <el-form-item
              :label="copy.phone"
              prop="phone"
              :error="profileErrors.phone"
            >
              <el-input
                v-model="form.phone"
                type="tel"
                :maxlength="limits.phone"
                autocomplete="tel"
                @input="profileErrors.phone = ''"
              />
            </el-form-item>
            <el-form-item
              class="bio-field"
              :label="copy.bio"
              prop="bio"
              :error="profileErrors.bio"
            >
              <el-input
                v-model="form.bio"
                type="textarea"
                :rows="limits.bioRows"
                :maxlength="limits.bio"
                show-word-limit
                :placeholder="copy.bioPlaceholder"
                @input="profileErrors.bio = ''"
              />
            </el-form-item>
          </div>
          <p
            v-if="profileError"
            class="inline-error"
            role="alert"
          >
            {{ profileError }}
          </p>
          <div class="form-footer">
            <span
              class="save-status"
              role="status"
            >{{ isDirty ? copy.unsaved : copy.saved }}</span>
            <div class="form-actions">
              <AppButton
                variant="ghost"
                :disabled="!isDirty || isSaving"
                @click="resetProfile"
              >
                {{ copy.reset }}
              </AppButton>
              <AppButton
                native-type="submit"
                :loading="isSaving"
                :disabled="!isDirty || isUploading"
              >
                {{ copy.save }}
              </AppButton>
            </div>
          </div>
        </el-form>
      </section>
      <section
        class="security-section"
        aria-labelledby="profile-security-title"
      >
        <div class="section-heading">
          <h2 id="profile-security-title">
            <ShieldCheck aria-hidden="true" />{{ copy.securityTitle }}
          </h2>
          <p>{{ copy.securityDescription }}</p>
        </div>
        <div class="password-summary">
          <span>{{ copy.passwordLabel }}</span>
          <AppButton
            ref="securityToggle"
            variant="secondary"
            :disabled="isChangingPassword"
            :aria-expanded="securityExpanded"
            aria-controls="profile-password-form"
            @click="toggleSecurity"
          >
            {{ securityExpanded ? copy.closePassword : copy.openPassword }}
            <ChevronDown
              class="security-chevron"
              :class="{ expanded: securityExpanded }"
              aria-hidden="true"
            />
          </AppButton>
        </div>
        <div
          v-show="securityExpanded"
          id="profile-password-form"
          class="password-details"
        >
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-position="top"
            :disabled="isChangingPassword"
            @submit.prevent="handleChangePassword"
          >
            <el-form-item
              :label="copy.oldPassword"
              prop="oldPassword"
              :error="passwordErrors.oldPassword"
            >
              <el-input
                ref="currentPasswordInput"
                v-model="passwordForm.oldPassword"
                type="password"
                show-password
                autocomplete="current-password"
                @input="passwordErrors.oldPassword = ''"
              />
            </el-form-item>
            <el-form-item
              :label="copy.newPassword"
              prop="newPassword"
              :error="passwordErrors.newPassword"
            >
              <el-input
                v-model="passwordForm.newPassword"
                type="password"
                show-password
                autocomplete="new-password"
                @input="passwordErrors.newPassword = ''"
              />
              <span class="field-hint">{{ copy.passwordHint }}</span>
            </el-form-item>
            <el-form-item
              :label="copy.confirmPassword"
              prop="newPasswordConfirm"
              :error="passwordErrors.newPasswordConfirm"
            >
              <el-input
                v-model="passwordForm.newPasswordConfirm"
                type="password"
                show-password
                autocomplete="new-password"
                @input="passwordErrors.newPasswordConfirm = ''"
              />
            </el-form-item>
            <p
              v-if="passwordError"
              class="inline-error"
              role="alert"
            >
              {{ passwordError }}
            </p>
            <AppButton
              variant="primary"
              native-type="submit"
              :loading="isChangingPassword"
            >
              {{ copy.changePassword }}
            </AppButton>
          </el-form>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { Upload, ShieldCheck, ChevronDown, Sparkles } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import AccountAvatar from '@/components/common/AccountAvatar.vue'
import { ACCOUNT_AVATAR } from '@/config/accountAvatar'
import { readAccountAvatar } from '@/utils/accountAvatar'
import { AVATAR_STUDIO as studio } from '@/config/avatarStudio'
import { PROFILE_COPY as copy, PROFILE_LIMITS as limits } from '@/config/personalCenter'
import { toProfileForm, normalizeProfile, getSettingsFieldErrors, getSettingsError } from '@/utils/personalCenter'
import AppButton from '@/components/common/AppButton.vue'
import PageHeader from '@/components/layout/PageHeader.vue'

const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()
const formRef = ref(null)
const passwordFormRef = ref(null)
const avatarInput = ref(null)
const securityExpanded = ref(false)
const securityToggle = ref(null)
const currentPasswordInput = ref(null)
const isFetching = ref(false)
const isSaving = ref(false)
const isChangingPassword = ref(false)
const isUploading = ref(false)
const loadError = ref('')
const profileError = ref('')
const passwordError = ref('')
const avatarError = ref('')
const profileErrors = reactive({})
const passwordErrors = reactive({})
const form = reactive(toProfileForm())
const baseline = ref(toProfileForm())
const passwordForm = reactive({ oldPassword: '', newPassword: '', newPasswordConfirm: '' })
const isDirty = computed(() => JSON.stringify(form) !== JSON.stringify(baseline.value))
const hasUnsavedInput = computed(() => isDirty.value || Object.values(passwordForm).some(Boolean))
const avatarIsImage = computed(() => readAccountAvatar(authStore.user).mode === 'image')
const rules = {
  username: [
    { required: true, whitespace: true, message: copy.requiredUsername, trigger: 'blur' },
    { pattern: /^[\p{L}\p{N}@.+_-]+$/u, message: copy.invalidUsername, trigger: 'blur' },
  ],
  email: [
    { required: true, message: copy.requiredEmail, trigger: 'blur' },
    { type: 'email', message: copy.invalidEmail, trigger: 'blur' },
  ],
}
const passwordRules = {
  oldPassword: [{ required: true, message: copy.requiredOldPassword, trigger: 'blur' }],
  newPassword: [
    { required: true, message: copy.requiredNewPassword, trigger: 'blur' },
    { min: limits.passwordMin, message: copy.shortPassword, trigger: 'blur' },
  ],
  newPasswordConfirm: [
    { required: true, message: copy.requiredConfirmation, trigger: 'blur' },
    { validator: (_rule, value, callback) => callback(value !== passwordForm.newPassword ? new Error(copy.mismatch) : undefined), trigger: 'blur' },
  ],
}

function clearErrors(errors) { Object.keys(errors).forEach(key => delete errors[key]) }
function resetProfile() {
  Object.assign(form, baseline.value)
  clearErrors(profileErrors)
  profileError.value = ''
  formRef.value?.clearValidate()
}
watch(() => authStore.user, user => {
  if (user && !isDirty.value) {
    baseline.value = toProfileForm(user)
    resetProfile()
  }
}, { immediate: true })
watch(() => passwordForm.newPassword, () => {
  if (passwordForm.newPasswordConfirm) passwordFormRef.value?.validateField('newPasswordConfirm').catch(() => {})
})

async function loadProfile() {
  if (isFetching.value) return
  isFetching.value = true
  loadError.value = ''
  try {
    const user = await authStore.fetchUserInfo()
    if (!user) loadError.value = copy.loadError
  } finally { isFetching.value = false }
}
async function handleSubmit() {
  if (isSaving.value || isUploading.value || !isDirty.value) return
  isSaving.value = true
  profileError.value = ''
  clearErrors(profileErrors)
  try {
    Object.assign(form, normalizeProfile(form))
    if (!await formRef.value?.validate().catch(() => false)) return
    const response = await authStore.updateProfile({ ...form })
    baseline.value = toProfileForm(response)
    resetProfile()
    appStore.success(copy.profileSuccess)
  } catch (error) {
    Object.assign(profileErrors, getSettingsFieldErrors(error))
    profileError.value = getSettingsError(error)
  } finally { isSaving.value = false }
}
async function handleChangePassword() {
  if (isChangingPassword.value) return
  isChangingPassword.value = true
  let passwordChanged = false
  passwordError.value = ''
  clearErrors(passwordErrors)
  try {
    if (!await passwordFormRef.value?.validate().catch(() => false)) return
    await authStore.changePassword({ ...passwordForm })
    Object.keys(passwordForm).forEach(key => passwordForm[key] = '')
    passwordFormRef.value?.clearValidate()
    securityExpanded.value = false
    passwordChanged = true
  } catch (error) {
    Object.assign(passwordErrors, getSettingsFieldErrors(error))
    passwordError.value = getSettingsError(error, copy.passwordError)
  } finally {
    isChangingPassword.value = false
    if (passwordChanged) {
      await nextTick()
      securityToggle.value?.$el?.focus()
      appStore.success(copy.passwordSuccess)
    }
  }
}
async function toggleSecurity() {
  securityExpanded.value = !securityExpanded.value
  if (securityExpanded.value) {
    await nextTick()
    currentPasswordInput.value?.focus()
  }
}
async function switchAvatarMode() {
  if (isUploading.value || isSaving.value) return
  isUploading.value = true
  avatarError.value = ''
  try {
    await authStore.updateProfile({ avatarPreferences: { mode: avatarIsImage.value ? 'robot' : 'image' } })
    appStore.success(copy.avatarSuccess)
  } catch (error) { avatarError.value = getSettingsError(error, copy.avatarError) }
  finally { isUploading.value = false }
}
async function uploadAvatar(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  avatarError.value = ''
  if (!file || isUploading.value || isSaving.value) return
  if (!limits.avatarTypes.includes(file.type)) { avatarError.value = copy.avatarTypeError; return }
  if (file.size > limits.avatarBytes) { avatarError.value = copy.avatarSizeError; return }
  isUploading.value = true
  try {
    await authStore.uploadAvatar(file)
    appStore.success(copy.avatarSuccess)
  } catch (error) { avatarError.value = getSettingsError(error, copy.avatarError) }
  finally { isUploading.value = false }
}
async function removeAvatar() {
  if (isUploading.value || isSaving.value) return
  isUploading.value = true
  avatarError.value = ''
  try {
    await authStore.removeAvatar()
    appStore.success(copy.avatarRemoved)
  } catch (error) { avatarError.value = getSettingsError(error, copy.avatarError) }
  finally { isUploading.value = false }
}
function beforeUnload(event) {
  if (!hasUnsavedInput.value) return
  event.preventDefault()
  event.returnValue = ''
}
onBeforeRouteLeave(() => {
  if (isSaving.value || isUploading.value || isChangingPassword.value) return false
  if (!hasUnsavedInput.value) return true
  return appStore.confirm({ title: copy.leaveTitle, message: copy.leaveMessage, confirmText: copy.leave, cancelText: copy.stay })
})
onMounted(() => {
  if (!authStore.user) loadProfile()
  window.addEventListener('beforeunload', beforeUnload)
})
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnload))
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
@use '@/assets/styles/personal-center.scss' as *;

.profile-columns { display: grid; grid-template-columns: minmax(0, 1fr) $personal-center-security-width; gap: $spacing-6; align-items: start; }
.profile-section, .security-section { min-width: 0; padding: $spacing-6; background: var(--bg-secondary); border: 1px solid var(--border-primary); border-radius: $radius-xl; }
.profile-section { container: profile-fields / inline-size; }
.profile-identity { display: flex; align-items: center; gap: $spacing-4; padding-bottom: $spacing-5; margin-bottom: $spacing-5; border-bottom: 1px solid var(--border-primary); }
.identity-details { flex: 1; min-width: 0; }
.identity-details strong { color: var(--text-primary); font-size: $font-size-sm; font-weight: $font-weight-medium; }
.avatar-actions { display: flex; flex-wrap: wrap; gap: $spacing-2; flex-shrink: 0; }
.avatar-actions svg, .section-heading svg, .security-chevron { width: $spacing-4; height: $spacing-4; flex-shrink: 0; }
.avatar-input { display: none; }
.profile-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: $spacing-5; align-items: start; }
.profile-fields > *, .name-fields > * { min-width: 0; }
.bio-field { grid-column: 1 / -1; }
.name-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: $spacing-3; }
.form-footer { border-top: 1px solid var(--border-primary); padding-top: $spacing-4; }
.password-summary { display: flex; flex-direction: column; align-items: flex-start; gap: $spacing-3; color: var(--text-primary); font-size: $font-size-sm; }
.password-details { padding-top: $spacing-5; margin-top: $spacing-5; border-top: 1px solid var(--border-primary); }
.security-chevron { transition: transform $transition-fast; &.expanded { transform: rotate(180deg); } }
@container personal-center (max-width: #{$personal-center-profile-breakpoint}) {
  .profile-columns { grid-template-columns: minmax(0, 1fr); }
  .password-summary { flex-direction: row; justify-content: space-between; align-items: center; }
}
@container profile-fields (max-width: #{$personal-center-fields-breakpoint}) {
  .profile-fields { grid-template-columns: minmax(0, 1fr); }
  .profile-identity { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: start; gap: $spacing-3; }
  .profile-identity :deep(.account-avatar) { grid-row: span 2; }
  .avatar-actions { grid-column: 2; }
}
@media (max-width: $breakpoint-sm) {
  .profile-section, .security-section { padding: $spacing-4; }
  .profile-columns { gap: $spacing-4; }
}
@media (prefers-reduced-motion: reduce) { .security-chevron { transition: none; } }
</style>

