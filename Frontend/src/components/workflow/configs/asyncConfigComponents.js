/**
 * 异步加载节点配置组件，打破 Editor ↔ PropertyPanel ↔ 重型配置 的 HMR 循环依赖。
 */
import { defineAsyncComponent } from 'vue'

function lazy(importFn) {
  return defineAsyncComponent(importFn)
}

export const DatasetUploadConfig = lazy(() => import('./DatasetUploadConfig.vue'))
export const DataAnnotationConfig = lazy(() => import('./DataAnnotationConfig.vue'))
export const DataAugmentationConfig = lazy(() => import('./DataAugmentationConfig.vue'))
export const ModelTrainingConfig = lazy(() => import('./ModelTrainingConfig.vue'))
export const YoloTrainingConfig = lazy(() => import('./YoloTrainingConfig.vue'))
