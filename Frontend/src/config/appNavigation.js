import { Home, GitBranch, Bot, MessageSquare, Database, Users, BarChart2, FileText, BookOpen, Network, Cpu, HardDrive, Terminal, Store, History, Compass, Star, GitCompare, Globe, Workflow, Weight, Boxes, Activity } from 'lucide-vue-next'
import { excludePersonalCenterModules } from '@/config/userNavigation'

const sections = [
  { id: 'delivery', label: '应用交付', accent: 'emerald', items: [
    { path: '/home', label: '交付工作台', icon: Home, accent: 'emerald' },
    { path: '/applications', label: '应用中心', icon: Boxes, accent: 'emerald' },
    { path: '/knowledge', label: '知识库', icon: Database, accent: 'emerald' },
    { path: '/workflows', label: '工作流', icon: GitBranch, accent: 'blue' },
    { path: '/executions', label: '执行记录', icon: History, accent: 'emerald' },
    { path: '/monitoring', label: '运行监控', icon: Activity, accent: 'emerald' },
  ] },
  { id: 'build', label: '构建能力', accent: 'blue', items: [
    { path: '/models', label: '模型管理', icon: Cpu, accent: 'cyan' },
    { path: '/agents', label: '智能体', icon: Bot, accent: 'violet' },
    { path: '/nl-create', label: '语创', icon: MessageSquare, accent: 'violet' },
    { path: '/prompts', label: '提示词', icon: FileText, accent: 'violet' },
  ] },
  { id: 'advanced', label: '高级工具', accent: 'cyan', defaultCollapsed: true, items: [
    { path: '/my-sites', label: '模型应用网站', icon: Globe, accent: 'blue' },
    { path: '/my-weights', label: '我的权重', icon: Weight, accent: 'cyan' },
    { path: '/vector-stores', label: '向量存储', icon: HardDrive, accent: 'cyan' },
    { path: '/datasets', label: '数据集', icon: BookOpen, accent: 'cyan' },
    { path: '/dataset-recommend', label: '数据集推荐', icon: Compass, accent: 'cyan' },
    { path: '/agents/collaborate', label: '多智能体协作', icon: Workflow, accent: 'violet' },
    { path: '/codegraph', label: '代码图谱', icon: Network, accent: 'amber' },
    { path: '/api-explorer', label: 'API 测试', icon: Terminal, accent: 'amber' },
    { path: '/workflows/diff', label: '工作流对比', icon: GitCompare, accent: 'amber' },
  ] },
  { id: 'workspace', label: '团队与资源', accent: 'amber', defaultCollapsed: true, items: [
    { path: '/team', label: '团队', icon: Users, accent: 'blue' },
    { path: '/analytics', label: '数据分析', icon: BarChart2, accent: 'amber' },
    { path: '/marketplace', label: '模板市场', icon: Store, accent: 'amber' },
    { path: '/my-templates', label: '我的模板', icon: Star, accent: 'amber' },
    { path: '/agents/marketplace', label: '智能体市场', icon: Store, accent: 'violet' },
  ] },
]

export const APP_NAV_SECTIONS = Object.freeze(sections.map(section => Object.freeze({
  ...section,
  items: Object.freeze(excludePersonalCenterModules(section.items).map(item => Object.freeze(item))),
})))
export const APP_NAV_ITEMS = Object.freeze(APP_NAV_SECTIONS.flatMap(section => section.items))
export const NAVIGATION_UI = Object.freeze({
  newApplication: Object.freeze({ path: '/applications?create=1', label: '创建应用' }),
  personalCenter: Object.freeze({ path: '/settings', label: '个人中心', accent: 'neutral' }),
  account: Object.freeze({ path: '/settings/profile', label: '账户', accent: 'neutral' }),
  upgrade: Object.freeze({ path: '/settings/billing', label: '升级套餐', accent: 'amber' }),
  generatedProjects: Object.freeze({ label: '识别项目' }),
  sectionId: id => `nav-section-${id}`,
  sectionLabel: label => `${label}导航分组`,
})
