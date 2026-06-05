"""
URL configuration for codegraph app.
"""

from django.urls import path
from . import views

app_name = 'codegraph'

urlpatterns = [
    # 项目相关
    path('projects/', views.ProjectListView.as_view(), name='project-list'),
    path('projects/<int:project_id>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('projects/<int:project_id>/structure/', views.ProjectStructureView.as_view(), name='project-structure'),
    path('projects/<int:project_id>/graph/', views.GraphDataView.as_view(), name='project-graph'),
    path('projects/<int:project_id>/stats/', views.GraphStatsView.as_view(), name='project-stats'),
    path('projects/<int:project_id>/analyze/', views.AnalyzeView.as_view(), name='project-analyze'),
    path('projects/<int:project_id>/cache/', views.CacheInvalidateView.as_view(), name='cache-invalidate'),
    
    # 模块相关
    path('projects/<int:project_id>/modules/', views.ModuleListView.as_view(), name='module-list'),
    path('projects/<int:project_id>/modules/dependencies/', views.ModuleDependencyView.as_view(), name='module-dependencies'),
    
    # 文件相关
    path('projects/<int:project_id>/file/', views.FileContentView.as_view(), name='file-content'),
    
    # 搜索
    path('projects/<int:project_id>/search/', views.SearchView.as_view(), name='search'),
    
    # WebSocket 状态
    path('ws-status/', views.ws_status, name='ws-status'),
]
