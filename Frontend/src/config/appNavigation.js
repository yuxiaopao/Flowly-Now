import { Home, GitBranch, Bot, MessageSquare, Database, Users, BarChart2, FileText, BookOpen, Network, Cpu, HardDrive, Terminal, Store, History, Compass, Star, GitCompare, Globe, Workflow, Weight } from 'lucide-vue-next'
import { excludePersonalCenterModules } from '@/config/userNavigation'

const sections = [
  { id: 'workspace', label: '工作空间', accent: 'blue', items: [
    { path: '/home', label: '工作台', icon: Home, accent: 'blue' },
    { path: '/workflows', label: '工作流', icon: GitBranch, accent: 'blue' },
    { path: '/my-sites', label: '我的网站', icon: Globe, accent: 'blue' },
    { path: '/team', label: '团队', icon: Users, accent: 'blue' },
  ] },
  { id: 'intelligence', label: '智能与创作', accent: 'violet', items: [
    { path: '/agents', label: '智能体', icon: Bot, accent: 'violet' },
    { path: '/agents/collaborate', label: '多智能体协作', icon: Workflow, accent: 'violet' },
    { path: '/nl-create', label: '语创', icon: MessageSquare, accent: 'violet' },
    { path: '/prompts', label: '提示词', icon: FileText, accent: 'violet' },
    { path: '/agents/marketplace', label: '智能体市场', icon: Store, accent: 'violet' },
  ] },
  { id: 'data', label: '模型与数据', accent: 'cyan', items: [
    { path: '/models', label: '模型管理', icon: Cpu, accent: 'cyan' },
    { path: '/my-weights', label: '我的权重', icon: Weight, accent: 'cyan' },
    { path: '/knowledge', label: '知识库', icon: Database, accent: 'cyan' },
    { path: '/vector-stores', label: '向量存储', icon: HardDrive, accent: 'cyan' },
    { path: '/datasets', label: '数据集', icon: BookOpen, accent: 'cyan' },
    { path: '/dataset-recommend', label: '数据集推荐', icon: Compass, accent: 'cyan' },
  ] },
  { id: 'tools', label: '工具与资源', accent: 'amber', items: [
    { path: '/executions', label: '执行历史', icon: History, accent: 'emerald' },
    { path: '/analytics', label: '数据分析', icon: BarChart2, accent: 'amber' },
    { path: '/marketplace', label: '模板市场', icon: Store, accent: 'amber' },
    { path: '/my-templates', label: '我的模板', icon: Star, accent: 'amber' },
    { path: '/codegraph', label: '代码图谱', icon: Network, accent: 'amber' },
    { path: '/api-explorer', label: 'API 测试', icon: Terminal, accent: 'amber' },
    { path: '/workflows/diff', label: '工作流对比', icon: GitCompare, accent: 'amber' },
  ] },
]

export const APP_NAV_SECTIONS = Object.freeze(sections.map(section => Object.freeze({
  ...section,
  items: Object.freeze(excludePersonalCenterModules(section.items).map(item => Object.freeze(item))),
})))
export const APP_NAV_ITEMS = Object.freeze(APP_NAV_SECTIONS.flatMap(section => section.items))
export const NAVIGATION_UI = Object.freeze({
  newWorkflow: Object.freeze({ path: '/workflows/new', label: '新建工作流' }),
  personalCenter: Object.freeze({ path: '/settings', label: '个人中心', accent: 'neutral' }),
  generatedProjects: Object.freeze({ label: '识别项目' }),
  sectionId: id => `nav-section-${id}`,
  sectionLabel: label => `${label}导航分组`,
})
