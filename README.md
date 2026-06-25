# Worldcup2026 Passion Realtime

这是 GitHub Pages 静态前端版本。页面静态资源托管在 GitHub Pages，实时数据接口来自已部署的 FastAPI 服务：

- GitHub Pages：https://sj-lin2025.github.io/Worldcup2026-Passion-Realtime/
- 后端服务：https://3vqhuzow.cn-east-fn.bytedance.net
- 数据接口：`/api/state`、`/api/refresh`、`/api/events`

GitHub Pages 仅支持静态文件，因此本仓库中的 `static/app.js` 使用绝对 API 地址访问后端服务。
