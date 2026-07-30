<template>
  <div class="article-page">
    <header class="article-nav">
      <button class="nav-back" @click="$router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <span class="nav-title">文章</span>
      <button class="nav-share" @click="copyLink">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
      </button>
    </header>

    <div v-if="entry" class="article-scroll">
      <article class="article-content">
        <h1 class="article-title">{{ entry.title }}</h1>
        <div class="article-meta">
          <span v-for="tag in entry.tags" :key="tag" class="article-tag">{{ tag }}</span>
          <span class="article-date">{{ formatDate(entry.updated_at || entry.created_at) }}</span>
        </div>
        <div class="article-divider" />
        <!-- 目录 -->
        <nav v-if="toc.length > 1" class="article-toc">
          <h4>目录</h4>
          <a v-for="item in toc" :key="item.id" :href="`#${item.id}`" class="toc-item" :style="{ paddingLeft: (item.level - 1) * 14 + 'px' }">{{ item.text }}</a>
        </nav>
        <div class="article-body" ref="bodyRef" v-html="renderedContent" />

        <!-- 参考来源 -->
        <div v-if="sources.length" class="article-sources">
          <h3>参考来源</h3>
          <a v-for="(s, i) in sources" :key="i" :href="s.url" target="_blank" class="source-item">
            <span class="source-num">{{ i + 1 }}</span>
            <span>{{ s.title || s.url }}</span>
          </a>
        </div>

        <!-- 反向链接 -->
        <div v-if="backlinks.length" class="article-backlinks">
          <h3>被以下页面引用（{{ backlinks.length }}）</h3>
          <router-link v-for="b in backlinks" :key="b.slug" :to="`/wiki/read/${b.slug}`" class="backlink-item">
            <span class="bl-arrow">→</span>
            {{ b.title }}
            <span class="bl-slug">{{ b.slug }}</span>
          </router-link>
        </div>

        <!-- 关联图谱 -->
        <div v-if="linkedPages.length" class="article-graph">
          <h3>关联页面</h3>
          <div class="graph-nodes">
            <span class="graph-node current">📍 {{ entry?.title }}</span>
            <router-link v-for="p in linkedPages" :key="p.slug" :to="`/wiki/read/${p.slug}`" class="graph-node link">
              {{ p.title }}
            </router-link>
          </div>
        </div>
      </article>
    </div>

    <div v-else-if="error" class="article-error">
      <p>{{ error }}</p>
    </div>
    <div v-else class="article-loading">加载中...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const entry = ref<any>(null)
const backlinks = ref<any[]>([])
const sources = ref<any[]>([])
const error = ref('')
const bodyRef = ref<HTMLElement>()

const toc = computed(() => {
  if (!entry.value?.content) return []
  const headings = entry.value.content.match(/^#{1,3} .+$/gm) || []
  return headings.map(h => {
    const level = (h.match(/^#+/) || ['#'])[0].length
    const text = h.replace(/^#+\s*/, '')
    const id = slugify(text)
    return { id, text, level }
  })
})

const linkedPages = computed(() => {
  if (!entry.value?.content) return []
  const refs = entry.value.content.match(/\[\[([^\]]+)\]\]/g) || []
  return [...new Set(refs)].map(r => {
    const slug = r.replace(/\[\[|\]\]/g, '')
    return { slug, title: slug.replace(/-/g, ' ') }
  })
})

const renderedContent = computed(() => {
  if (!entry.value?.content) return ''
  let html = entry.value.content
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    .replace(/^### (.+)$/gm, (_, t) => `<h3 id="${slugify(t)}">${t}</h3>`)
    .replace(/^## (.+)$/gm, (_, t) => `<h2 id="${slugify(t)}">${t}</h2>`)
    .replace(/^# (.+)$/gm, (_, t) => `<h2 id="${slugify(t)}">${t}</h2>`)
    .replace(/\[\[([^\]]+)\]\]/g, '<a href="/wiki/read/$1" class="internal-link">$1</a>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(\d+)\. (.+)$/gm, '<li>$2</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
  return '<p>' + html + '</p>'
})

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  try { return new Date(dateStr).toLocaleDateString('zh-CN') } catch { return dateStr }
}

function copyLink() {
  navigator.clipboard?.writeText(window.location.href)
}

function slugify(text: string) {
  return text.toLowerCase().replace(/[^\w\u4e00-\u9fff]+/g, '-').replace(/^-|-$/g, '')
}

onMounted(async () => {
  const slug = route.params.slug as string
  try {
    const res = await fetch(`/api/wiki/${slug}`)
    if (!res.ok) { error.value = '文章未找到'; return }
    entry.value = await res.json()

    try {
      const blRes = await fetch(`/api/wiki/${slug}/backlinks`)
      if (blRes.ok) {
        const blData = await blRes.json()
        backlinks.value = blData.backlinks || []
        sources.value = blData.sources || []
      }
    } catch {}
  } catch {
    error.value = '加载失败'
  }
})
</script>

<style scoped>
.article-page {
  min-height: 100vh; min-height: 100dvh;
  background: var(--ios-bg-primary, #000);
  color: var(--ios-text-primary, #f5f5f7);
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* 导航 */
.article-nav {
  display: flex; align-items: center; justify-content: space-between;
  height: 44px; padding: 0 12px;
  position: sticky; top: 0; z-index: 10;
  background: var(--ios-bg-primary, #000);
  border-bottom: 0.5px solid var(--ios-separator, #3a3a3c);
}
.nav-back, .nav-share {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  border: none; background: none; color: var(--ios-blue, #0a84ff); cursor: pointer;
  border-radius: 50%;
}
.nav-back:active, .nav-share:active { background: var(--ios-fill-secondary, #3a3a3c); }
.nav-title { font-size: 17px; font-weight: 600; }

.article-scroll { overflow-y: auto; }

/* 内容区 */
.article-content {
  max-width: 680px; margin: 0 auto; padding: 32px 20px 80px;
}
.article-title {
  font-size: 32px; font-weight: 800; line-height: 1.25;
  margin: 0 0 16px; letter-spacing: -0.5px;
}
.article-meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 20px; }
.article-tag {
  font-size: 12px; padding: 3px 10px; border-radius: 10px;
  background: var(--ios-fill-secondary, #3a3a3c);
  color: var(--ios-text-secondary, #a1a1a6);
}
.article-date { font-size: 13px; color: var(--ios-text-tertiary, #555); }
.article-divider { height: 0.5px; background: var(--ios-separator, #3a3a3c); margin-bottom: 28px; }

/* 正文 */
.article-body { font-size: 17px; line-height: 1.8; }
.article-body :deep(h2) { font-size: 24px; font-weight: 700; margin: 36px 0 14px; }
.article-body :deep(h3) { font-size: 20px; font-weight: 600; margin: 28px 0 10px; }
.article-body :deep(p) { margin: 0 0 16px; }
.article-body :deep(li) { margin: 6px 0; padding-left: 4px; }
.article-body :deep(ul), .article-body :deep(ol) { padding-left: 24px; margin: 8px 0 16px; }
.article-body :deep(code) {
  background: var(--ios-bg-tertiary, #2c2c2e); padding: 2px 6px;
  border-radius: 4px; font-size: 0.9em; font-family: 'SF Mono', Menlo, monospace;
}
.article-body :deep(pre) {
  background: var(--ios-bg-secondary, #1c1c1e); padding: 16px 20px;
  border-radius: 12px; overflow-x: auto; margin: 16px 0;
  border: 0.5px solid var(--ios-separator, #3a3a3c);
}
.article-body :deep(pre code) { background: none; padding: 0; }
.article-body :deep(a) { color: var(--ios-blue, #0a84ff); text-decoration: none; }
.article-body :deep(a:hover) { text-decoration: underline; }
.article-body :deep(strong) { font-weight: 700; }
.article-body :deep(blockquote) {
  border-left: 3px solid var(--ios-blue, #0a84ff);
  padding-left: 16px; margin: 16px 0; color: var(--ios-text-secondary, #a1a1a6);
}
.article-body :deep(.internal-link) { border-bottom: 1px dashed var(--ios-blue, #0a84ff); }

/* 目录 */
.article-toc {
  margin-bottom: 24px; padding: 16px 18px;
  background: var(--ios-bg-secondary, #1c1c1e);
  border-radius: 12px; border: 0.5px solid var(--ios-separator, #3a3a3c);
}
.article-toc h4 { font-size: 13px; color: var(--ios-text-secondary, #a1a1a6); margin: 0 0 10px; }
.toc-item {
  display: block; font-size: 14px; color: var(--ios-text-secondary, #a1a1a6);
  text-decoration: none; padding: 3px 0; border-radius: 4px;
  transition: color 0.15s;
}
.toc-item:hover { color: var(--ios-blue, #0a84ff); }
.article-sources { margin-top: 40px; padding-top: 20px; border-top: 0.5px solid var(--ios-separator, #3a3a3c); }
.article-sources h3 { font-size: 14px; color: var(--ios-text-secondary, #a1a1a6); margin: 0 0 12px; }
.source-item {
  display: flex; gap: 10px; padding: 8px 0; font-size: 13px;
  color: var(--ios-blue, #0a84ff); text-decoration: none;
  border-bottom: 0.5px solid var(--ios-separator, #3a3a3c);
}
.source-num {
  width: 20px; height: 20px; display: flex; align-items: center; justify-content: center;
  border-radius: 50%; background: var(--ios-fill-secondary, #3a3a3c);
  font-size: 11px; flex-shrink: 0;
}

/* 反向链接 */
.article-backlinks { margin-top: 40px; padding-top: 20px; border-top: 0.5px solid var(--ios-separator, #3a3a3c); }
.article-backlinks h3 { font-size: 14px; color: var(--ios-text-secondary, #a1a1a6); margin: 0 0 10px; }
.backlink-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  font-size: 14px; color: var(--ios-blue, #0a84ff); text-decoration: none;
  border-radius: 8px; margin-bottom: 4px;
  transition: background 0.15s;
}
.backlink-item:hover { background: var(--ios-fill-secondary, #1c1c1e); }
.bl-arrow { font-size: 12px; color: var(--ios-text-tertiary, #555); }
.bl-slug { font-size: 11px; color: var(--ios-text-tertiary, #555); margin-left: auto; }

/* 关联图谱 */
.article-graph { margin-top: 32px; padding-top: 16px; border-top: 0.5px solid var(--ios-separator, #3a3a3c); }
.article-graph h3 { font-size: 14px; color: var(--ios-text-secondary, #a1a1a6); margin: 0 0 12px; }
.graph-nodes { display: flex; flex-wrap: wrap; gap: 8px; }
.graph-node {
  display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px;
  border-radius: 16px; font-size: 13px; text-decoration: none;
  border: 0.5px solid var(--ios-separator, #3a3a3c);
  transition: all 0.15s;
}
.graph-node.current { background: var(--ios-blue, #0a84ff); color: #fff; border-color: transparent; font-weight: 600; }
.graph-node.link { background: var(--ios-bg-secondary, #1c1c1e); color: var(--ios-text-primary, #fff); cursor: pointer; }
.graph-node.link:hover { border-color: var(--ios-blue, #0a84ff); }

.article-loading, .article-error {
  text-align: center; padding: 80px 20px;
  color: var(--ios-text-secondary, #555); font-size: 15px;
}
</style>
