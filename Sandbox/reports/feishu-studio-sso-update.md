## VeADK Studio 入口更新（2026-08-10）

> 后续统一使用飞书 SSO Studio，旧的本地 `uvx veadk-python==1.0.10 veadk studio` 方式已废弃。

### 推荐入口

`https://sicjgimgi9920l1mcqqdg.apigateway-cn-beijing.volceapi.com/`

### 实际验证

- 页面标题：AgentKit Studio。
- 飞书 SSO 自动登录成功。
- 当前身份：李孟桃，管理员。
- 通用智能体列表加载成功，可浏览北京地域 Runtime。
- Codex 智能体列表当前为空。
- OpenClaw 接口返回 HTTP 503：管理员未配置。
- Hermes 接口返回 HTTP 503：管理员未配置。

### 结论

SSO Studio 基础访问、账号认证和通用智能体能力通过。Codex、OpenClaw、Hermes 需要完成服务端管理员配置后再复验，不再引用旧本地 Studio 的成功状态作为当前结论。

验证截图：`Sandbox/screenshots/veadk-studio-sso.png`。
