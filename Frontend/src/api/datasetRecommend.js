import api from './index'

export const datasetRecommendApi = {
  getCategories: () => api.get('/dataset-recommend/categories/'),
  getDatasets: (params) => api.get('/dataset-recommend/datasets/', { params })
}
