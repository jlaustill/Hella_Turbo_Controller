import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
  },
  {
    path: '/actuators',
    name: 'Actuators',
    component: () => import('@/views/ActuatorManager.vue'),
  },
  {
    path: '/memory',
    name: 'Memory',
    component: () => import('@/views/MemoryViewer.vue'),
  },
  {
    path: '/can-monitor',
    name: 'CANMonitor',
    component: () => import('@/views/CANMonitor.vue'),
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/views/Analysis.vue'),
  },
];

export default routes;