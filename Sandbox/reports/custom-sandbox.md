# 自定义镜像与 Private Sandbox 实操记录

## 镜像构建

- Dockerfile：`Sandbox/samples/custom-sandbox/Dockerfile`
- 镜像：`agentkit-platform-2100045928-cn-beijing.cr.volces.com/limengtao_agentkit/lmt-custom-sandbox-image:v1`
- Pipeline：`1a999d9f449f4ee49f216f80df06b4d0`
- 构建内容：基于 AgentKit Code CLI 镜像，预装 `is-even@1.0.0`。

AgentKit CLI 已创建/复用 TOS 构建上下文、CR namespace/repository 与 Code Pipeline，并触发构建。该镜像地址已被 Private Tool 创建接口接受。

## Private Tool

- 名称：`lmt-custom-sandbox`
- Tool ID：`t-yesbywpurkkgnctgwj32`
- Session：`lmt-custom-session`
- 当前状态：`Ready`

镜像构建时的 npm 全局安装路径为 `/opt/nodejs/22/lib/node_modules`；使用该路径加载 `is-even` 并执行 `isEven(42)`，返回：

```text
LMT_CUSTOM_IMAGE_OK=true
```

命令退出码为 0，CUSTOM-03 判定通过。资源保留供检查。
