# 工作流项目 - 文件夹结构创建脚本
# 运行方式：在 PowerShell 中执行: .\setup-folders.ps1

Write-Host "开始创建项目文件夹结构..." -ForegroundColor Green

# 创建主项目目录
$projectRoot = "e:\Flowly-now\workflow-project"
New-Item -ItemType Directory -Path $projectRoot -Force | Out-Null

# 创建后端目录结构
$backendDirs = @(
    "backend",
    "backend/apps",
    "backend/configs",
    "backend/workflow",
    "backend/workflow/services",
    "backend/media",
    "backend/static"
)

foreach ($dir in $backendDirs) {
    $fullPath = Join-Path $projectRoot $dir
    New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    Write-Host "创建: $dir" -ForegroundColor Gray
}

# 创建前端目录结构
$frontendDirs = @(
    "frontend",
    "frontend/src",
    "frontend/src/api",
    "frontend/src/components",
    "frontend/src/views",
    "frontend/src/stores",
    "frontend/src/router",
    "frontend/src/utils",
    "frontend/src/assets",
    "frontend/public"
)

foreach ($dir in $frontendDirs) {
    $fullPath = Join-Path $projectRoot $dir
    New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    Write-Host "创建: $dir" -ForegroundColor Gray
}

# 创建文档和脚本目录
$otherDirs = @(
    "docs",
    "scripts",
    "logs"
)

foreach ($dir in $otherDirs) {
    $fullPath = Join-Path $projectRoot $dir
    New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    Write-Host "创建: $dir" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "文件夹结构创建完成！" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "项目位置: $projectRoot" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. 查看 docs/ 目录下的 complete-guide.md 文档" -ForegroundColor White
Write-Host "2. 按照文档步骤开始 Step 2 - 创建后端 Django 项目" -ForegroundColor White
Write-Host ""
