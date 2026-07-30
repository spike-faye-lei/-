/**
 * Vue Router 配置 — iOS 风格多页面
 */
import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
    {
        path: '/',
        name: 'chat',
        component: () => import(/* webpackChunkName: "chat" */ '../views/ChatPage.vue'),
    },
    {
        path: '/wiki',
        name: 'wiki',
        component: () => import(/* webpackChunkName: "wiki" */ '../views/WikiPage.vue'),
    },
    {
        path: '/wiki/read/:slug',
        name: 'article',
        component: () => import(/* webpackChunkName: "article" */ '../views/ArticlePage.vue'),
    },
    {
        path: '/face-auth',
        name: 'face',
        component: () => import(/* webpackChunkName: "face-auth" */ '../views/FacePage.vue'),
    },
    {
        path: '/settings',
        name: 'settings',
        component: () => import(/* webpackChunkName: "settings" */ '../views/SettingsPage.vue'),
    },
    {
        path: '/login',
        name: 'login',
        component: () => import(/* webpackChunkName: "login" */ '../views/LoginView.vue'),
    },
    {
        path: '/setup/:setupSecret',
        name: 'setup',
        component: () => import(/* webpackChunkName: "login" */ '../views/LoginView.vue'),
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
