/** UniPortal 工程隔离：从 URL 读取 portal_project_id，sessionStorage 兜底 */
export function getPortalProjectId() {
  const fromUrl = new URLSearchParams(window.location.search).get('portal_project_id')
  if (fromUrl) {
    sessionStorage.setItem('portalProjectId', fromUrl)
    return fromUrl
  }
  return sessionStorage.getItem('portalProjectId') || null
}

/** 路由/页面切换时刷新（URL 带新 portal_project_id 时更新 sessionStorage） */
export function refreshPortalProjectId() {
  return getPortalProjectId()
}

export function clearPortalProjectId() {
  sessionStorage.removeItem('portalProjectId')
}

/** 是否处于 UniPortal 工程上下文 */
export function isUniPortalMode() {
  return Boolean(getPortalProjectId())
}

/** 路由 query 中附带 portal_project_id（若存在） */
export function withPortalQuery(query = {}) {
  const portalProjectId = getPortalProjectId()
  if (portalProjectId) {
    return { ...query, portal_project_id: portalProjectId }
  }
  return query
}
